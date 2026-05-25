"""
WorkoutLog document.

Supports both manual logging and Health Connect sync.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.base import BaseDocument


class WorkoutLog(BaseDocument):
    # ── References ────────────────────────────────────────────────────────────
    user_id: UUID

    # ── Timing ────────────────────────────────────────────────────────────────
    logged_at: datetime = None  # type: ignore[assignment]

    def __init__(self, **data):  # type: ignore[override]
        if "logged_at" not in data or data["logged_at"] is None:
            data["logged_at"] = datetime.now(timezone.utc)
        super().__init__(**data)

    # ── Workout Identity ──────────────────────────────────────────────────────
    title: str
    # Valid: strength | cardio | hiit | yoga | sports | other
    workout_type: str = "other"
    duration_minutes: int
    # Valid: low | moderate | high | very_high
    intensity: str = "moderate"

    # ── Calories Out ──────────────────────────────────────────────────────────
    calories_burned: float | None = None
    # Source: health_connect | formula | manual
    calories_source: str = "manual"

    # ── Exercise Details (Strength Training) ──────────────────────────────────
    # [{name, sets, reps, weight_kg, duration_seconds}]
    exercises: list = []

    # ── Additional Context ────────────────────────────────────────────────────
    notes: str | None = None
    raw_input: str | None = None

    # ── Health Connect Integration ────────────────────────────────────────────
    health_connect_id: str | None = None

    # ── Soft Delete ───────────────────────────────────────────────────────────
    is_deleted: bool = False

    # ── Phase 2: Semantic Embedding ───────────────────────────────────────────
    embedding: list[float] | None = None

    class Settings:
        name = "workout_logs"

    def __repr__(self) -> str:
        return (
            f"<WorkoutLog id={self.id} title='{self.title}' "
            f"type={self.workout_type} duration={self.duration_minutes}min>"
        )
