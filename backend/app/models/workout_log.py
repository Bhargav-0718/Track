"""
WorkoutLog model.

Supports both:
1. Manual logging (user types "ran 5km for 30 min")
2. Health Connect sync (structured data from Android health platform)

The `exercises` JSONB field handles strength training:
[
    {"name": "Bench Press", "sets": 4, "reps": 8, "weight_kg": 80},
    {"name": "Incline DB Press", "sets": 3, "reps": 10, "weight_kg": 22},
]

Cardio doesn't need exercises — duration + intensity is sufficient for calorie estimation.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore[assignment]
    VECTOR_AVAILABLE = False


class WorkoutLog(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "workout_logs"
    __table_args__ = (
        Index("ix_workout_logs_user_date", "user_id", "logged_at"),
        Index("ix_workout_logs_user_type", "user_id", "workout_type"),
        # Health Connect dedup: unique external ID per user
        Index("ix_workout_logs_health_connect_id", "health_connect_id", unique=True,
              postgresql_where=__import__("sqlalchemy").text("health_connect_id IS NOT NULL")),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Timing ────────────────────────────────────────────────────────────────
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Workout Identity ──────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Valid: strength | cardio | hiit | yoga | sports | other
    workout_type: Mapped[str] = mapped_column(String(20), default="other", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Valid: low | moderate | high | very_high
    intensity: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)

    # ── Calories Out ──────────────────────────────────────────────────────────
    calories_burned: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Source: health_connect | formula | manual
    calories_source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)

    # ── Exercise Details (Strength Training) ──────────────────────────────────
    # [{name, sets, reps, weight_kg, duration_seconds}]
    exercises: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # ── Additional Context ────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Health Connect Integration ────────────────────────────────────────────
    # Unique ID from Android Health Connect for deduplication
    health_connect_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Phase 2: Semantic Memory ───────────────────────────────────────────────
    if VECTOR_AVAILABLE and Vector is not None:
        embedding: Mapped[list[float] | None] = mapped_column(
            Vector(1536), nullable=True
        )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="workout_logs", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<WorkoutLog id={self.id} title='{self.title}' "
            f"type={self.workout_type} duration={self.duration_minutes}min>"
        )
