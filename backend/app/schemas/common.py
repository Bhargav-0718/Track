"""
Shared schema types used across multiple resources.

Design principle: Schemas are the contract between the API and clients.
Keep them strict and explicit — never expose internal model fields directly.
"""
from datetime import datetime
from enum import StrEnum
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Enums ─────────────────────────────────────────────────────────────────────
# Using StrEnum so values serialize directly as strings in JSON

class MealType(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    PRE_WORKOUT = "pre_workout"
    POST_WORKOUT = "post_workout"


class EstimationSource(StrEnum):
    MEMORY = "memory"          # Retrieved from user's food_memory
    DATASET = "dataset"        # Retrieved from nutrition_cache (INDB)
    LLM = "llm"                # LLM fallback estimate
    MANUAL = "manual"          # User manually entered values
    PHOTO = "photo"            # Estimated from food photo (Phase 3)
    HEALTH_CONNECT = "health_connect"


class ConfidenceLevel(StrEnum):
    CONFIRMED = "confirmed"    # User-verified or high-confidence dataset hit
    ESTIMATED = "estimated"    # System estimate with moderate confidence
    UNCERTAIN = "uncertain"    # Low-confidence LLM estimate


class WorkoutType(StrEnum):
    STRENGTH = "strength"
    CARDIO = "cardio"
    HIIT = "hiit"
    YOGA = "yoga"
    SPORTS = "sports"
    OTHER = "other"


class Intensity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ActivityLevel(StrEnum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class FitnessGoal(StrEnum):
    LOSE_WEIGHT = "lose_weight"
    MAINTAIN = "maintain"
    GAIN_MUSCLE = "gain_muscle"
    IMPROVE_FITNESS = "improve_fitness"


class CorrectionType(StrEnum):
    CALORIES = "calories"
    PORTION = "portion"
    FOOD_NAME = "food_name"
    MEAL_TYPE = "meal_type"
    MACROS = "macros"


# ── Base Schema ────────────────────────────────────────────────────────────────

class TrackBaseSchema(BaseModel):
    """Base for all Track schemas. Enables from_attributes for ORM compatibility."""
    model_config = ConfigDict(
        from_attributes=True,        # Allow building from ORM models
        use_enum_values=True,        # Serialize enums as values (not names)
        populate_by_name=True,       # Allow both alias and field name
        str_strip_whitespace=True,   # Strip leading/trailing whitespace from strings
    )


# ── Response Envelope ──────────────────────────────────────────────────────────

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response envelope."""
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )


class ErrorResponse(BaseModel):
    """Standard error response body."""
    error: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: bool
    version: str
    environment: str
    timestamp: datetime


# ── Pagination Query Params ────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
