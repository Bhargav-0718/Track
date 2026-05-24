"""
Schemas for progress checkpoints and photo management.

Design:
- CheckpointCreate    : Input when creating a checkpoint (weight, date, notes, tags)
- CheckpointUpdate    : Partial update for checkpoint metadata
- PhotoResponse       : Single photo record (URL resolved, never raw storage_key)
- CheckpointResponse  : Full checkpoint with embedded photos
- CheckpointSummary   : Lightweight list-view (photo count, primary photo URL)
- CompareRequest      : Two checkpoint IDs to compare
- CompareResponse     : AI physique comparison result
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import TrackBaseSchema


# ── Photo Schemas ──────────────────────────────────────────────────────────────

class PhotoResponse(TrackBaseSchema):
    """A single progress photo — URL is resolved, storage_key is never exposed."""
    id: UUID
    checkpoint_id: UUID
    url: str                           # Resolved public URL (from storage backend)
    original_filename: str | None = None
    content_type: str
    file_size_bytes: int
    width_px: int
    height_px: int
    display_order: int
    label: str | None = None           # "front" | "back" | "side-left" | "side-right"
    created_at: datetime


# ── Checkpoint Schemas ─────────────────────────────────────────────────────────

class CheckpointCreate(TrackBaseSchema):
    """Create a new progress checkpoint."""
    checkpoint_date: date = Field(description="Date of this checkpoint (YYYY-MM-DD)")
    weight_kg: float | None = Field(
        default=None, gt=0, lt=500,
        description="Body weight in kg at this checkpoint"
    )
    body_fat_percentage: float | None = Field(
        default=None, gt=0, lt=100,
        description="Estimated or measured body fat percentage"
    )
    notes: str | None = Field(
        default=None, max_length=2000,
        description="Qualitative notes about this checkpoint"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Labels like ['end-of-cut', '12-week-mark']"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        if len(v) > 10:
            raise ValueError("Maximum 10 tags per checkpoint")
        return [tag.lower().strip()[:50] for tag in v if tag.strip()]


class CheckpointUpdate(TrackBaseSchema):
    """Partial update for checkpoint metadata. Photos are managed separately."""
    weight_kg: float | None = Field(default=None, gt=0, lt=500)
    body_fat_percentage: float | None = Field(default=None, gt=0, lt=100)
    notes: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = None
    checkpoint_date: date | None = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 tags per checkpoint")
        return [tag.lower().strip()[:50] for tag in v if tag.strip()]


class CheckpointSummary(TrackBaseSchema):
    """Lightweight checkpoint for list views — no full photo list."""
    id: UUID
    checkpoint_date: date
    weight_kg: float | None = None
    body_fat_percentage: float | None = None
    notes: str | None = None
    tags: list[str]
    photo_count: int = 0
    primary_photo_url: str | None = None   # First photo URL, if any
    created_at: datetime


class CheckpointResponse(TrackBaseSchema):
    """Full checkpoint detail with all photos."""
    id: UUID
    checkpoint_date: date
    weight_kg: float | None = None
    body_fat_percentage: float | None = None
    notes: str | None = None
    tags: list[str]
    photos: list[PhotoResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ── Comparison Schemas ─────────────────────────────────────────────────────────

class CompareRequest(TrackBaseSchema):
    """
    Request to compare two checkpoints using AI physique analysis.

    Before and after are identified by checkpoint ID.
    The AI receives one photo from each checkpoint (the primary photo, display_order=0).

    If either checkpoint has no photos, the comparison will fail with 422.
    """
    before_checkpoint_id: UUID = Field(description="ID of the 'before' checkpoint")
    after_checkpoint_id: UUID = Field(description="ID of the 'after' checkpoint")

    # Optional: specify exact photo IDs instead of using primary photos
    before_photo_id: UUID | None = Field(
        default=None,
        description="Specific photo from before checkpoint (defaults to primary)"
    )
    after_photo_id: UUID | None = Field(
        default=None,
        description="Specific photo from after checkpoint (defaults to primary)"
    )


class PhysiqueObservation(TrackBaseSchema):
    """A single structured observation from the AI analysis."""
    category: Literal[
        "overall", "fat_distribution", "muscle_definition",
        "posture", "waistline", "consistency"
    ]
    observation: str
    direction: Literal["positive", "neutral", "insufficient_data"] = "neutral"


class CompareResponse(TrackBaseSchema):
    """
    AI-generated physique comparison between two checkpoints.

    IMPORTANT: This is fitness observation, not medical advice.
    The AI is constrained to objective visual observations only.
    """
    before_checkpoint_id: UUID
    after_checkpoint_id: UUID
    before_date: date
    after_date: date
    days_elapsed: int

    # Body weight delta (if both checkpoints have weight data)
    weight_delta_kg: float | None = None

    # AI-generated content
    overall_summary: str = Field(
        description="2-3 sentence overview of visible changes"
    )
    observations: list[PhysiqueObservation] = Field(
        description="Structured per-category observations"
    )
    encouragement: str = Field(
        description="Positive motivational closing message"
    )
    confidence_note: str = Field(
        description="Caveat about the limitations of visual assessment"
    )
    overall_progress: Literal[
        "significant_progress", "steady_progress",
        "maintenance", "insufficient_data"
    ]

    # Which model generated this (for transparency)
    analysis_model: str = "gpt-4o"

    # Disclaimer always included
    disclaimer: str = (
        "This analysis is for fitness tracking purposes only and does not "
        "constitute medical advice. Consult a healthcare professional for "
        "any health concerns."
    )
