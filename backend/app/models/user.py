"""
User model.

Stores identity, physical stats, and fitness goals.
Physical stats (weight_kg) represent user-reported values, not Health Connect data.
Health Connect data flows through daily_summaries and workout_logs.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.correction_event import CorrectionEvent
    from app.models.daily_report import DailyReport
    from app.models.daily_summary import DailySummary
    from app.models.food_log import FoodLog
    from app.models.food_memory import FoodMemory
    from app.models.progress_checkpoint import ProgressCheckpoint
    from app.models.user_preference import UserPreference
    from app.models.workout_log import WorkoutLog


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_lower", "email", postgresql_ops={"email": "text_ops"}),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Profile ───────────────────────────────────────────────────────────────
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)  # Current user-reported weight

    # ── Goals ─────────────────────────────────────────────────────────────────
    # Enum values stored as strings for portability (avoids PG enum migration pain)
    # Valid: sedentary | light | moderate | active | very_active
    activity_level: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    # Valid: lose_weight | maintain | gain_muscle | improve_fitness
    goal: Mapped[str] = mapped_column(String(30), default="maintain", nullable=False)

    # ── Targets ───────────────────────────────────────────────────────────────
    # Null = system-calculated from TDEE formula; set = user-override
    target_calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    food_logs: Mapped[list[FoodLog]] = relationship(
        "FoodLog", back_populates="user", lazy="noload", cascade="all, delete-orphan"
    )
    workout_logs: Mapped[list[WorkoutLog]] = relationship(
        "WorkoutLog", back_populates="user", lazy="noload", cascade="all, delete-orphan"
    )
    food_memories: Mapped[list[FoodMemory]] = relationship(
        "FoodMemory", back_populates="user", lazy="noload", cascade="all, delete-orphan"
    )
    daily_summaries: Mapped[list[DailySummary]] = relationship(
        "DailySummary", back_populates="user", lazy="noload", cascade="all, delete-orphan"
    )
    correction_events: Mapped[list[CorrectionEvent]] = relationship(
        "CorrectionEvent", back_populates="user", lazy="noload", cascade="all, delete-orphan"
    )
    preference: Mapped[UserPreference | None] = relationship(
        "UserPreference", back_populates="user", lazy="noload", uselist=False,
        cascade="all, delete-orphan"
    )
    progress_checkpoints: Mapped[list[ProgressCheckpoint]] = relationship(
        "ProgressCheckpoint", back_populates="user", lazy="noload",
        cascade="all, delete-orphan"
    )
    daily_reports: Mapped[list[DailyReport]] = relationship(
        "DailyReport", back_populates="user", lazy="noload",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
