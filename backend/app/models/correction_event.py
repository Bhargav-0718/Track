"""
CorrectionEvent — records every time a user corrects an AI estimate.

Primary feedback signal for Phase 4 adaptive learning.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field


class CorrectionEvent(Document):
    """Correction events don't need updated_at — they are immutable records."""
    id: UUID = Field(default_factory=uuid4)  # type: ignore[assignment]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ── References ────────────────────────────────────────────────────────────
    user_id: UUID
    food_log_id: UUID | None = None

    # ── Correction Details ────────────────────────────────────────────────────
    # Valid: calories | portion | food_name | meal_type | macros
    correction_type: str

    # Numeric corrections
    original_value: float | None = None
    corrected_value: float | None = None
    delta: float | None = None

    # Text corrections
    original_text: str | None = None
    corrected_text: str | None = None

    # Source metadata
    original_estimation_source: str | None = None
    original_confidence_score: float | None = None

    # ── Flexible Metadata ─────────────────────────────────────────────────────
    metadata_: dict = {}

    class Settings:
        name = "correction_events"

    def __repr__(self) -> str:
        return (
            f"<CorrectionEvent id={self.id} type={self.correction_type} "
            f"delta={self.delta}>"
        )
