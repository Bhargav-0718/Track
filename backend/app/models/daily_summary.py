"""
DailySummary — pre-aggregated daily nutrition and activity snapshot.

Updated every time a food_log or workout_log is created/updated/deleted.
This is a materialized-style table (not a view) for fast dashboard queries.

Design rationale: Rather than aggregating food_logs on every dashboard request
(expensive as history grows), we maintain a running summary that's updated
transactionally with each log operation.

Also serves as the Health Connect sync anchor — stores steps, active minutes,
and whether the day has been synced with Android Health Connect.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class DailySummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_summaries"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_summary_user_date"),
        Index("ix_daily_summaries_user_date", "user_id", "date"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Nutrition In ──────────────────────────────────────────────────────────
    total_calories_in: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_protein_g: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_carbs_g: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_fat_g: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_fiber_g: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    food_log_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Calories Out ──────────────────────────────────────────────────────────
    total_calories_out: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    workout_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Activity (Health Connect) ─────────────────────────────────────────────
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Calories from steps/activity (Health Connect TDEE data)
    activity_calories: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Computed ──────────────────────────────────────────────────────────────
    # net = calories_in - calories_out (negative = deficit, positive = surplus)
    net_calories: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Health Connect Sync ───────────────────────────────────────────────────
    health_connect_synced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="daily_summaries", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<DailySummary id={self.id} user={self.user_id} "
            f"date={self.date} cal_in={self.total_calories_in} cal_out={self.total_calories_out}>"
        )
