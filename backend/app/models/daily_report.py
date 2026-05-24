"""
DailyReport — AI-generated nightly summary of the user's day.

Generated once per day (typically at configured report_time, default 21:00).
Includes:
  - Calorie and macro summary vs targets
  - Workout summary
  - Consistency score (computed from behavioral analytics)
  - AI-generated narrative insights
  - Motivational message
  - Behavioral observations (pattern-based, not ML)

Phase 4: Core output of the adaptive reporting system.

Design notes:
- One report per user per day (enforced by UniqueConstraint)
- report_style is snapshotted at generation time (user may change preference later)
- was_shown/user_rating enable future preference learning
- calorie_summary and workout_summary are JSONB for schema flexibility
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class DailyReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_reports"
    __table_args__ = (
        # One report per user per date
        UniqueConstraint("user_id", "report_date", name="uq_daily_reports_user_date"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Report Identity ───────────────────────────────────────────────────────
    report_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Computed Metrics (stored for fast retrieval) ───────────────────────────
    # Calories: {"target": 2000, "actual": 1850, "adherence_pct": 92.5, "deficit": -150}
    calorie_summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Workouts: {"count": 1, "total_calories_burned": 350, "net_calories": 1500, "types": ["strength"]}
    workout_summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Macros: {"protein_g": 150, "protein_target": 180, "carbs_g": 200, "fat_g": 65}
    macro_summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Score 0.0–1.0 representing how consistent the user was that day
    consistency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Current consecutive logging streak at report time
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 7-day logging consistency at report time (0.0–1.0)
    weekly_consistency: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # ── AI-Generated Content ───────────────────────────────────────────────────
    # 2-3 paragraph narrative summary
    insights_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Short motivational message (1-2 sentences)
    motivation_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # List of pattern-based observations:
    # ["You under-eat protein on rest days", "Your streak is your longest this month"]
    behavioral_observations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # ── Report Style ───────────────────────────────────────────────────────────
    # Snapshotted from user preference at generation time
    # Valid: motivational | analytical | brief | detailed
    report_style: Mapped[str] = mapped_column(
        String(20), default="motivational", nullable=False
    )

    # Which LLM generated this report (for future A/B testing)
    generation_model: Mapped[str] = mapped_column(
        String(50), default="gpt-4o-mini", nullable=False
    )

    # ── Engagement Tracking ───────────────────────────────────────────────────
    # Was the report displayed to the user?
    was_shown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Optional user rating (1-5 stars). Feeds preference learning in future.
    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="daily_reports", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<DailyReport id={self.id} "
            f"date={self.report_date} score={self.consistency_score:.2f}>"
        )
