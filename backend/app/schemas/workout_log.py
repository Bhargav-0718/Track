"""
WorkoutLog request/response schemas.

Exercise entries (for strength training) use a flexible structure:
{
    "name": "Bench Press",
    "sets": 4,
    "reps": 8,
    "weight_kg": 80.0,
    "duration_seconds": null   # for cardio-style exercises
}
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import Intensity, TrackBaseSchema, WorkoutType


# ── Nested Schemas ─────────────────────────────────────────────────────────────

class ExerciseEntry(TrackBaseSchema):
    """A single exercise within a workout."""
    name: str = Field(max_length=255)
    sets: int | None = Field(default=None, ge=1, le=100)
    reps: int | None = Field(default=None, ge=1, le=1000)
    weight_kg: float | None = Field(default=None, ge=0.0, le=1000.0)
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    distance_km: float | None = Field(default=None, ge=0.0, le=1000.0)
    notes: str | None = Field(default=None, max_length=500)


# ── Request Schemas ────────────────────────────────────────────────────────────

class WorkoutLogCreate(TrackBaseSchema):
    """Body for POST /api/v1/workout-logs/"""
    title: str = Field(min_length=1, max_length=255)
    workout_type: WorkoutType = WorkoutType.OTHER
    duration_minutes: int = Field(ge=1, le=1440)  # 1 min to 24 hours
    intensity: Intensity = Intensity.MODERATE
    calories_burned: float | None = Field(default=None, ge=0.0, le=10000.0)
    exercises: list[ExerciseEntry] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)
    raw_input: str | None = Field(default=None, max_length=1000)
    logged_at: datetime | None = None
    # Health Connect integration
    health_connect_id: str | None = Field(default=None, max_length=255)


class WorkoutLogUpdate(TrackBaseSchema):
    """Body for PUT /api/v1/workout-logs/{log_id} — all optional."""
    title: str | None = Field(default=None, min_length=1, max_length=255)
    workout_type: WorkoutType | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    intensity: Intensity | None = None
    calories_burned: float | None = Field(default=None, ge=0.0, le=10000.0)
    exercises: list[ExerciseEntry] | None = None
    notes: str | None = Field(default=None, max_length=2000)
    logged_at: datetime | None = None


class HealthConnectWorkoutSync(TrackBaseSchema):
    """Batch sync from Android Health Connect."""
    workouts: list[WorkoutLogCreate]


# ── Response Schemas ───────────────────────────────────────────────────────────

class WorkoutLogResponse(TrackBaseSchema):
    """Full workout log response."""
    id: UUID
    user_id: UUID
    logged_at: datetime
    created_at: datetime
    updated_at: datetime

    title: str
    workout_type: str
    duration_minutes: int
    intensity: str
    calories_burned: float | None
    calories_source: str
    exercises: list[dict]
    notes: str | None
    health_connect_id: str | None


class WorkoutLogSummary(TrackBaseSchema):
    """Lightweight workout log for list views."""
    id: UUID
    logged_at: datetime
    title: str
    workout_type: str
    duration_minutes: int
    calories_burned: float | None
    intensity: str
