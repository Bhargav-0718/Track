"""
UserFoodItem — a user's personally-defined food portions.

Each entry represents one specific portion variant of a food (e.g. "1 plate poha"
vs "1 bowl poha" are two separate entries) with calorie/macro values the user has
confirmed themselves. These take priority over AI estimation when matched.
"""
from __future__ import annotations

from uuid import UUID

from pymongo import ASCENDING

from app.models.base import BaseDocument


class UserFoodItem(BaseDocument):
    user_id: UUID

    # ── Identity ──────────────────────────────────────────────────────────────
    food_name: str          # canonical lowercase name, e.g. "poha" — used for search/grouping
    display_name: str       # original casing, e.g. "Poha"
    unit_label: str         # e.g. "plate", "bowl", "roti" — distinguishes portions of the same food
    portion_description: str  # full display text, e.g. "1 plate poha"

    # ── Nutrition (for this exact portion) ──────────────────────────────────────
    calories: float
    portion_grams: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None

    use_count: int = 1

    class Settings:
        name = "user_food_items"
        indexes = [
            [("user_id", ASCENDING), ("food_name", ASCENDING), ("unit_label", ASCENDING)],
        ]
