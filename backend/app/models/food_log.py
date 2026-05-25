"""
FoodLog document — the core data record of the platform.

Every food entry captures what the user typed, what the system understood,
nutrition values, confidence metadata, and correction history.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.base import BaseDocument


class FoodLog(BaseDocument):
    # ── References ────────────────────────────────────────────────────────────
    user_id: UUID
    nutrition_cache_id: UUID | None = None
    memory_id: UUID | None = None

    # ── Timing ────────────────────────────────────────────────────────────────
    logged_at: datetime = None  # type: ignore[assignment]

    def __init__(self, **data):  # type: ignore[override]
        if "logged_at" not in data or data["logged_at"] is None:
            data["logged_at"] = datetime.now(timezone.utc)
        super().__init__(**data)

    # ── Raw Input ─────────────────────────────────────────────────────────────
    raw_input: str | None = None

    # ── Meal Classification ───────────────────────────────────────────────────
    meal_type: str = "snack"

    # ── Food Identity ─────────────────────────────────────────────────────────
    food_name: str
    brand_name: str | None = None
    portion_description: str | None = None
    portion_grams: float | None = None

    # ── Nutrition ─────────────────────────────────────────────────────────────
    calories: float
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None

    # ── Estimation Metadata ───────────────────────────────────────────────────
    estimation_source: str = "manual"
    confidence_score: float = 1.0
    confidence_level: str = "confirmed"
    assumptions: list = []

    # ── Correction Tracking ───────────────────────────────────────────────────
    is_corrected: bool = False
    original_calories: float | None = None
    original_portion_grams: float | None = None

    # ── Soft Delete ───────────────────────────────────────────────────────────
    is_deleted: bool = False

    # ── Phase 3: Photo ────────────────────────────────────────────────────────
    image_url: str | None = None

    # ── Phase 2: Semantic Embedding ───────────────────────────────────────────
    embedding: list[float] | None = None

    class Settings:
        name = "food_logs"

    def __repr__(self) -> str:
        return (
            f"<FoodLog id={self.id} food='{self.food_name}' "
            f"calories={self.calories} source={self.estimation_source}>"
        )
