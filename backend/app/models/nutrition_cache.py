"""
NutritionCache — authoritative nutrition data from external databases.

Stores per-100g nutrition facts. Searched using Python string similarity
(replaces pg_trgm fuzzy search). TTL-based cache for freshness.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from beanie import Indexed
from pymongo import ASCENDING

from app.models.base import BaseDocument


class NutritionCache(BaseDocument):
    # ── Source ────────────────────────────────────────────────────────────────
    # Valid: usda | open_food_facts | manual
    source: str = "usda"
    external_id: str | None = None
    food_name: str

    # ── Per-100g Nutrition ────────────────────────────────────────────────────
    calories_per_100g: float
    protein_per_100g: float | None = None
    carbs_per_100g: float | None = None
    fat_per_100g: float | None = None
    fiber_per_100g: float | None = None
    sodium_per_100g: float | None = None
    sugar_per_100g: float | None = None

    # ── Cache Metadata ────────────────────────────────────────────────────────
    raw_data: dict = {}
    expires_at: datetime | None = None

    class Settings:
        name = "nutrition_cache"
        indexes = [
            # Unique per source + external_id
            [("source", ASCENDING), ("external_id", ASCENDING)],
        ]

    def __repr__(self) -> str:
        return (
            f"<NutritionCache id={self.id} source={self.source} "
            f"food='{self.food_name}' cal={self.calories_per_100g}/100g>"
        )
