"""
DailySummary response schemas.

The daily summary is the primary dashboard data structure.
It aggregates: food logs + workout logs + Health Connect activity.
"""
from datetime import date
from uuid import UUID

from app.schemas.common import TrackBaseSchema
from app.schemas.food_log import FoodLogSummary
from app.schemas.workout_log import WorkoutLogSummary


class NutritionTargetProgress(TrackBaseSchema):
    """Progress toward daily nutrition targets."""
    target: float | None
    actual: float
    remaining: float | None
    percentage: float | None  # 0-100


class DailySummaryResponse(TrackBaseSchema):
    """Full daily summary for dashboard view."""
    id: UUID
    user_id: UUID
    date: date

    # Nutrition In
    total_calories_in: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    food_log_count: int

    # Calories Out
    total_calories_out: float
    workout_count: int

    # Activity
    steps: int | None
    active_minutes: int | None
    activity_calories: float | None

    # Computed
    net_calories: float | None

    # Sync status
    health_connect_synced: bool

    # Notes
    notes: str | None


class DashboardResponse(TrackBaseSchema):
    """Complete dashboard data for a single day."""
    summary: DailySummaryResponse
    food_logs: list[FoodLogSummary]
    workout_logs: list[WorkoutLogSummary]

    # Progress toward targets (null if no target set)
    calorie_progress: NutritionTargetProgress
    protein_progress: NutritionTargetProgress


class HealthConnectSyncRequest(TrackBaseSchema):
    """Body for POST /api/v1/health-connect/sync"""
    date: date
    steps: int | None = None
    active_minutes: int | None = None
    activity_calories: float | None = None


class HealthConnectSyncResponse(TrackBaseSchema):
    """Response from Health Connect sync."""
    synced: bool
    date: date
    steps: int | None
    active_minutes: int | None
