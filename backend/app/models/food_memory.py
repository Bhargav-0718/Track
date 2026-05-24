"""
FoodMemory — the semantic memory store for personalized food recognition.

This is the Phase 2 intelligence layer, pre-provisioned in Phase 1.

Every time a user logs the same food, this record gets smarter:
- avg_calories updates via weighted average (corrections weighted higher)
- log_count tracks frequency (high frequency = high confidence)
- correction_count tracks how often the system was wrong (used in confidence decay)
- embedding enables semantic similarity search ("dal chawal" ≈ "dal rice" ≈ "lentil rice")
- aliases collects all the ways the user has referred to this food

The confidence_score formula (Phase 2):
    base = min(log_count / 10, 0.9)           # More logs = more confident
    correction_penalty = correction_count * 0.1  # Each correction reduces confidence
    final = max(base - correction_penalty, 0.2)  # Floor at 0.2 (never fully distrust)
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore[assignment]
    VECTOR_AVAILABLE = False


class FoodMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_memory"
    __table_args__ = (
        UniqueConstraint("user_id", "canonical_name", name="uq_food_memory_user_food"),
        Index("ix_food_memory_user_id", "user_id"),
        Index("ix_food_memory_last_logged", "user_id", "last_logged_at"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Food Identity ─────────────────────────────────────────────────────────
    # Canonical: normalized name used as the unique key ("Dal Chawal")
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # All user input strings that mapped to this food
    aliases: Mapped[list] = mapped_column(ARRAY(String), default=list, nullable=False)

    # ── Learned Nutrition (Weighted Averages) ─────────────────────────────────
    avg_calories: Mapped[float] = mapped_column(Float, nullable=False)
    avg_portion_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Learning Signals ──────────────────────────────────────────────────────
    log_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    correction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_logged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Confidence ────────────────────────────────────────────────────────────
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # ── Semantic Embedding (Phase 2) ───────────────────────────────────────────
    # Vector of canonical_name + portion_description for similarity search
    if VECTOR_AVAILABLE and Vector is not None:
        embedding: Mapped[list[float] | None] = mapped_column(
            Vector(1536), nullable=True
        )

    # ── Flexible Metadata ─────────────────────────────────────────────────────
    # cuisine_type, typical_meal_type, dietary_flags, etc.
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="food_memories", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<FoodMemory id={self.id} food='{self.canonical_name}' "
            f"logs={self.log_count} confidence={self.confidence_score:.2f}>"
        )
