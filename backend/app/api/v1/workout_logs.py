"""
Workout log endpoints.

Routes:
  POST   /workout-logs/           → Create workout log
  GET    /workout-logs/           → List workout logs (paginated)
  GET    /workout-logs/{id}       → Get specific workout
  PUT    /workout-logs/{id}       → Update workout
  DELETE /workout-logs/{id}       → Soft delete workout
  POST   /health-connect/sync     → Sync activity data from Android Health Connect
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, CurrentUserID, DbSession
from app.schemas.common import PaginatedResponse
from app.schemas.daily_summary import (
    DashboardResponse,
    HealthConnectSyncRequest,
    HealthConnectSyncResponse,
)
from app.schemas.workout_log import (
    WorkoutLogCreate,
    WorkoutLogResponse,
    WorkoutLogSummary,
    WorkoutLogUpdate,
)
from app.services.daily_summary_service import DailySummaryService
from app.services.workout_service import WorkoutService

router = APIRouter(tags=["workout-logs"])


@router.post(
    "/workout-logs/",
    response_model=WorkoutLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a workout",
)
async def create_workout_log(
    data: WorkoutLogCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> WorkoutLogResponse:
    """
    Log a workout.

    If `calories_burned` is not provided, the system estimates using
    MET (Metabolic Equivalent of Task) formula based on workout type,
    intensity, and duration. The estimate is labeled `calories_source: formula`.

    For Health Connect synced workouts, provide `health_connect_id` for
    automatic deduplication.
    """
    service = WorkoutService(db)
    return await service.create_log(
        current_user.id,
        data,
        user_weight_kg=current_user.weight_kg,
    )


@router.get(
    "/workout-logs/",
    response_model=PaginatedResponse[WorkoutLogSummary],
    summary="List workout logs",
)
async def list_workout_logs(
    current_user_id: CurrentUserID,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    workout_type: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> PaginatedResponse[WorkoutLogSummary]:
    """List workout logs with pagination and optional filters."""
    service = WorkoutService(db)
    logs, total = await service.list_logs(
        current_user_id,
        page=page,
        page_size=page_size,
        workout_type=workout_type,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedResponse.create(
        items=logs,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/workout-logs/{log_id}",
    response_model=WorkoutLogResponse,
    summary="Get a specific workout log",
)
async def get_workout_log(
    log_id: UUID,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> WorkoutLogResponse:
    """Get full details of a specific workout log."""
    service = WorkoutService(db)
    return await service.get_log(log_id, current_user_id)


@router.put(
    "/workout-logs/{log_id}",
    response_model=WorkoutLogResponse,
    summary="Update a workout log",
)
async def update_workout_log(
    log_id: UUID,
    data: WorkoutLogUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> WorkoutLogResponse:
    """
    Update a workout log.

    If workout_type, intensity, or duration_minutes are changed and
    the original calories_source was 'formula', calories are automatically
    re-estimated. Provide explicit calories_burned to override.
    """
    service = WorkoutService(db)
    return await service.update_log(
        log_id,
        current_user.id,
        data,
        user_weight_kg=current_user.weight_kg,
    )


@router.delete(
    "/workout-logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workout log",
)
async def delete_workout_log(
    log_id: UUID,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> None:
    """Soft delete a workout log and refresh daily summary."""
    service = WorkoutService(db)
    await service.delete_log(log_id, current_user_id)


# ── Dashboard ─────────────���───────────────────────────���────────────────────────

@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    tags=["dashboard"],
    summary="Get daily dashboard",
)
async def get_dashboard(
    current_user_id: CurrentUserID,
    db: DbSession,
    date: date | None = Query(default=None, description="Date (YYYY-MM-DD). Defaults to today."),
) -> DashboardResponse:
    """
    Get the complete dashboard for a specific day.

    Returns: daily summary + food logs + workout logs + progress toward targets.
    This is the primary endpoint for the Flutter home screen.
    """
    service = DailySummaryService(db)
    return await service.get_dashboard(current_user_id, date)


# ── Health Connect Sync ───────────────��────────────────────────────��────────────

@router.post(
    "/health-connect/sync",
    response_model=HealthConnectSyncResponse,
    tags=["health-connect"],
    summary="Sync activity data from Android Health Connect",
)
async def sync_health_connect(
    data: HealthConnectSyncRequest,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> HealthConnectSyncResponse:
    """
    Receive activity data from Android Health Connect.

    Called by the Flutter app after reading:
    - Steps count
    - Active minutes
    - Activity calories burned

    Data is upserted into the daily summary for the specified date.
    """
    service = DailySummaryService(db)
    return await service.sync_health_connect(current_user_id, data)
