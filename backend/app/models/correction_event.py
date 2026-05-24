"""
CorrectionEvent — records every time a user corrects an AI estimate.

This is the primary feedback signal for Phase 4 adaptive learning.

Why store corrections as events rather than just updating the log?
1. Audit trail: We can see exactly how wrong the system was
2. Pattern analysis: Identify systematic biases (always underestimates Indian food)
3. Memory adaptation: Weight recent corrections higher in food_memory updates
4. Model evaluation: Track accuracy improvement over time

Examples of what gets captured:
- User changes calories from 420 to 350 (delta: -70)
- User changes portion from "medium bowl" to "large bowl"
- User changes food name from "chicken curry" to "chicken tikka masala"
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.food_log import FoodLog
    from app.models.user import User


class CorrectionEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "correction_events"
    __table_args__ = (
        Index("ix_correction_events_user_id", "user_id"),
        Index("ix_correction_events_food_log_id", "food_log_id"),
        # Phase 4: analyze correction patterns over time
        Index("ix_correction_events_user_created", "user_id", "created_at"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    food_log_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("food_logs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Correction Details ────────────────────────────────────────────────────
    # Valid: calories | portion | food_name | meal_type | macros
    correction_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Numeric corrections (for calories and portion)
    original_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Computed delta (corrected - original); negative = system overestimated
    delta: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Text corrections (for food name, meal type)
    original_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    corrected_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Source of the original estimate being corrected
    original_estimation_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    original_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="correction_events", lazy="noload")
    food_log: Mapped[FoodLog | None] = relationship(
        "FoodLog", back_populates="correction_events", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<CorrectionEvent id={self.id} type={self.correction_type} "
            f"delta={self.delta}>"
        )
