"""
NutritionCache — authoritative nutrition data from external databases.

This is the first lookup in the calorie estimation pipeline (before LLM).
Prevents hallucination by grounding estimates in real nutritional data.

Sources (in priority order):
1. USDA FoodData Central (authoritative, free API)
2. Open Food Facts (branded/packaged foods, community-maintained)
3. Manual (admin-entered for common regional foods not in USDA)

Cache strategy:
- TTL of 30 days (nutrition data doesn't change often)
- External ID preserved for source attribution
- Raw data stored for future re-parsing without new API calls
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NutritionCache(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_cache"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_nutrition_cache_source_id"),
        Index("ix_nutrition_cache_food_name", "food_name"),
        # TTL-based cleanup: find expired entries
        Index("ix_nutrition_cache_expires_at", "expires_at"),
    )

    # ── Source ────────────────────────────────────────────────────────────────
    # Valid: usda | open_food_facts | manual
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="usda")
    # External database ID for source attribution and dedup
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Human-readable name from the source database
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Per-100g Nutrition ────────────────────────────────────────────────────
    # Stored per 100g to enable portion-based calculation
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sugar_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Cache Metadata ────────────────────────────────────────────────────────
    # Full source API response stored for future use without re-fetching
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<NutritionCache id={self.id} source={self.source} "
            f"food='{self.food_name}' cal={self.calories_per_100g}/100g>"
        )
