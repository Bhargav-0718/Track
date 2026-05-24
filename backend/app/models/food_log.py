"""
FoodLog model — the core data record of the platform.

Every food entry captures:
1. What the user typed (raw_input) — preserved for re-parsing
2. What the system understood (food_name, portion)
3. Nutrition values and their confidence
4. How the estimate was derived (estimation_source + assumptions)
5. Whether the user corrected it

This rich metadata enables:
- Phase 2: Semantic search, memory building, confidence weighting
- Phase 3: Photo-to-log correlation
- Phase 4: Behavioral pattern analysis, accuracy improvement tracking
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.correction_event import CorrectionEvent
    from app.models.food_memory import FoodMemory
    from app.models.nutrition_cache import NutritionCache
    from app.models.user import User

# Try to import pgvector; gracefully degrade if not installed yet
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore[assignment]
    VECTOR_AVAILABLE = False


class FoodLog(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "food_logs"
    __table_args__ = (
        # Most common query: user's logs for a specific day
        Index("ix_food_logs_user_date", "user_id", "logged_at"),
        # Meal type filtering
        Index("ix_food_logs_user_meal_type", "user_id", "meal_type"),
        # Estimation source analysis (for Phase 4 accuracy tracking)
        Index("ix_food_logs_estimation_source", "estimation_source"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nutrition_cache_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("nutrition_cache.id", ondelete="SET NULL"),
        nullable=True,
    )
    memory_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("food_memory.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Timing ────────────────────────────────────────────────────────────────
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Raw Input ─────────────────────────────────────────────────────────────
    # Preserved verbatim — enables re-parsing with improved AI models in future
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Meal Classification ───────────────────────────────────────────────────
    # Valid: breakfast | lunch | dinner | snack | pre_workout | post_workout
    meal_type: Mapped[str] = mapped_column(String(20), default="snack", nullable=False)

    # ── Food Identity ─────────────────────────────────────────────────────────
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portion_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portion_grams: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Nutrition ─────────────────────────────────────────────────────────────
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Estimation Metadata ───────────────────────────────────────────────────
    # Source: memory | dataset | llm | manual | health_connect
    estimation_source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    # 0.0 = completely uncertain, 1.0 = user-confirmed or high-confidence dataset
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    # Enum for UI: confirmed | estimated | uncertain
    confidence_level: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    # List of human-readable assumptions: ["Assumed medium bowl = 200g", "Used generic dal recipe"]
    assumptions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # ── Correction Tracking ───────────────────────────────────────────────────
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Store original value when user corrects — enables delta analysis in Phase 4
    original_calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_portion_grams: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Phase 3: Photo ────────────────────────────────────────────────────────
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Phase 2: Semantic Memory ───────────────────────────────────────────────
    # Pre-provisioned: populated when embedding pipeline is built in Phase 2
    # Dimension must match openai_embedding_dimensions in config (1536)
    if VECTOR_AVAILABLE and Vector is not None:
        embedding: Mapped[list[float] | None] = mapped_column(
            Vector(1536), nullable=True
        )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="food_logs", lazy="noload")
    nutrition_cache: Mapped[NutritionCache | None] = relationship(
        "NutritionCache", lazy="noload"
    )
    food_memory: Mapped[FoodMemory | None] = relationship(
        "FoodMemory", foreign_keys=[memory_id], lazy="noload"
    )
    correction_events: Mapped[list[CorrectionEvent]] = relationship(
        "CorrectionEvent", back_populates="food_log", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<FoodLog id={self.id} food='{self.food_name}' "
            f"calories={self.calories} source={self.estimation_source}>"
        )
