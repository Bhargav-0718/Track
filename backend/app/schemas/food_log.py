"""
FoodLog request/response schemas.

Key design decision: The client always sends raw_input (what user typed).
The server parses and estimates — never trust client-provided calorie values
unless estimation_source = 'manual' (user explicitly entered exact values).

Three logging modes:
1. Quick log: raw_input only → server parses + estimates
2. Manual log: full nutrition values → stored as-is with source='manual'
3. Corrected log: update existing log with user's verified values
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import (
    ConfidenceLevel,
    EstimationSource,
    MealType,
    TrackBaseSchema,
)


# ── Nested Schemas ─────────────────────────────────────────────────────────────

class NutritionData(TrackBaseSchema):
    """Macro and micro nutrition values."""
    calories: float = Field(ge=0.0, le=10000.0)
    protein_g: float | None = Field(default=None, ge=0.0, le=1000.0)
    carbs_g: float | None = Field(default=None, ge=0.0, le=2000.0)
    fat_g: float | None = Field(default=None, ge=0.0, le=500.0)
    fiber_g: float | None = Field(default=None, ge=0.0, le=200.0)


class PortionData(TrackBaseSchema):
    """Portion size in human-readable and metric forms."""
    description: str | None = Field(default=None, max_length=255,
                                     description="e.g. 'medium bowl', '2 pieces'")
    grams: float | None = Field(default=None, ge=0.0, le=10000.0)


# ── Request Schemas ────────────────────────────────────────────────────────────

class FoodLogCreate(TrackBaseSchema):
    """
    Body for POST /api/v1/food-logs/

    Two valid modes:
    1. Quick: provide raw_input only. Server estimates nutrition via AI pipeline.
    2. Manual: provide food_name + calories (+ optionally macros). Stored directly.
    """
    # Quick log mode: user types natural language
    raw_input: str | None = Field(
        default=None,
        max_length=1000,
        description="Natural language input: 'dal chawal medium bowl'",
    )

    # Manual mode: user provides exact values
    food_name: str | None = Field(default=None, max_length=255)
    brand_name: str | None = Field(default=None, max_length=255)
    portion_description: str | None = Field(default=None, max_length=255)
    portion_grams: float | None = Field(default=None, ge=0.0, le=10000.0)
    calories: float | None = Field(default=None, ge=0.0, le=10000.0)
    protein_g: float | None = Field(default=None, ge=0.0, le=1000.0)
    carbs_g: float | None = Field(default=None, ge=0.0, le=2000.0)
    fat_g: float | None = Field(default=None, ge=0.0, le=500.0)
    fiber_g: float | None = Field(default=None, ge=0.0, le=200.0)

    meal_type: MealType = MealType.SNACK
    logged_at: datetime | None = Field(
        default=None,
        description="When the food was actually eaten. Defaults to now.",
    )

    @model_validator(mode="after")
    def validate_input_mode(self) -> "FoodLogCreate":
        has_raw = self.raw_input is not None and len(self.raw_input.strip()) > 0
        has_manual = self.food_name is not None and self.calories is not None

        if not has_raw and not has_manual:
            raise ValueError(
                "Provide either raw_input (quick log) or "
                "food_name + calories (manual log)"
            )
        return self

    @property
    def is_quick_log(self) -> bool:
        return self.raw_input is not None and len(self.raw_input.strip()) > 0

    @property
    def is_manual_log(self) -> bool:
        return self.food_name is not None and self.calories is not None


class FoodLogUpdate(TrackBaseSchema):
    """
    Body for PUT /api/v1/food-logs/{log_id}

    Used for user corrections. When calories or portion are changed,
    a CorrectionEvent is automatically recorded.
    """
    food_name: str | None = Field(default=None, max_length=255)
    brand_name: str | None = Field(default=None, max_length=255)
    portion_description: str | None = Field(default=None, max_length=255)
    portion_grams: float | None = Field(default=None, ge=0.0, le=10000.0)
    calories: float | None = Field(default=None, ge=0.0, le=10000.0)
    protein_g: float | None = Field(default=None, ge=0.0, le=1000.0)
    carbs_g: float | None = Field(default=None, ge=0.0, le=2000.0)
    fat_g: float | None = Field(default=None, ge=0.0, le=500.0)
    fiber_g: float | None = Field(default=None, ge=0.0, le=200.0)
    meal_type: MealType | None = None
    logged_at: datetime | None = None


# ── Response Schemas ───────────────────────────────────────────────────────────

class FoodLogResponse(TrackBaseSchema):
    """Full food log response."""
    id: UUID
    user_id: UUID
    logged_at: datetime
    created_at: datetime
    updated_at: datetime

    raw_input: str | None
    meal_type: str
    food_name: str
    brand_name: str | None
    portion_description: str | None
    portion_grams: float | None

    calories: float
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None

    estimation_source: str
    confidence_score: float
    confidence_level: str
    assumptions: list[str]

    is_corrected: bool
    original_calories: float | None

    image_url: str | None


class FoodLogSummary(TrackBaseSchema):
    """Lightweight food log for list views."""
    id: UUID
    logged_at: datetime
    meal_type: str
    food_name: str
    calories: float
    confidence_level: str
    estimation_source: str
    is_corrected: bool


class DailyFoodSummary(TrackBaseSchema):
    """Aggregated daily nutrition from food logs."""
    date: str  # ISO date string "YYYY-MM-DD"
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    food_count: int
    logs: list[FoodLogSummary]
