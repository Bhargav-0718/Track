"""
ProgressCheckpoint — a dated physique snapshot with metadata.

A checkpoint is a moment-in-time record of the user's body metrics and optional
photos. Users create checkpoints at meaningful milestones:
  - End of a cut/bulk phase
  - After N weeks of training
  - Monthly check-ins

Each checkpoint can have multiple photos (ProgressPhoto records).
Two checkpoints can be compared using the AI physique comparison engine.

Phase 3: Core progress tracking model.
Phase 4: Source of trend data for behavioral analysis.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.progress_photo import ProgressPhoto
    from app.models.user import User


class ProgressCheckpoint(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "progress_checkpoints"
    __table_args__ = (
        # Most common query: user's checkpoints ordered by date
        Index("ix_progress_checkpoints_user_date", "user_id", "checkpoint_date"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Checkpoint Date ────────────────────────────────────────────────────────
    # Stored as a Date (not DateTime) — the time doesn't matter for checkpoints
    checkpoint_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Body Metrics (optional — user may skip measurements) ──────────────────
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_fat_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Qualitative Context ───────────────────────────────────────────────────
    # Free-form notes: "End of 12-week cut, feeling great"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tags for filtering: ["end-of-cut", "12-week", "before-vacation"]
    tags: Mapped[list] = mapped_column(ARRAY(String(50)), default=list, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="progress_checkpoints", lazy="noload"
    )
    photos: Mapped[list[ProgressPhoto]] = relationship(
        "ProgressPhoto",
        back_populates="checkpoint",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="ProgressPhoto.display_order",
    )

    def __repr__(self) -> str:
        return (
            f"<ProgressCheckpoint id={self.id} "
            f"date={self.checkpoint_date} weight={self.weight_kg}kg>"
        )
