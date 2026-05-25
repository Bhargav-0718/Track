"""
Food log endpoints.

Routes:
  POST   /food-logs/            → Create food log (quick or manual)
  GET    /food-logs/            → List food logs (paginated, filterable)
  GET    /food-logs/recent      → Get recently logged foods (quick-add)
  GET    /food-logs/daily       → Get daily summary + all logs for a date
  GET    /food-logs/{id}        → Get specific food log
  PUT    /food-logs/{id}        → Update/correct food log
  DELETE /food-logs/{id}        → Soft delete food log
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserID
from app.schemas.common import PaginatedResponse
from app.schemas.food_log import (
    DailyFoodSummary,
    FoodLogCreate,
    FoodLogResponse,
    FoodLogSummary,
    FoodLogUpdate,
)
from app.services.food_service import FoodService

router = APIRouter(prefix="/food-logs", tags=["food-logs"])


@router.post(
    "/",
    response_model=FoodLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a food entry",
)
async def create_food_log(
    data: FoodLogCreate,
    current_user_id: CurrentUserID,
) -> FoodLogResponse:
    """
    Log a food entry.

    **Quick log mode**: Provide `raw_input` with natural language description.
    AI estimation pipeline runs: memory → INDB dataset → LLM fallback.

    **Manual mode**: Provide `food_name` + `calories` (and optionally macros).
    Stored directly with `confidence_level: confirmed`.

    The `logged_at` field defaults to now — pass a custom timestamp to log
    meals that were eaten earlier.
    """
    service = FoodService()
    return await service.create_log(current_user_id, data)


@router.get(
    "/recent",
    response_model=list[FoodLogSummary],
    summary="Get recently logged foods for quick-add",
)
async def get_recent_foods(
    current_user_id: CurrentUserID,
    limit: int = Query(default=20, ge=1, le=50),
) -> list[FoodLogSummary]:
    """
    Get recently and frequently logged foods.
    Used for quick-add suggestions in the Flutter UI.
    Returns deduplicated foods ordered by most recently logged.
    """
    service = FoodService()
    return await service.get_recent_foods(current_user_id, limit=limit)


@router.get(
    "/daily",
    response_model=DailyFoodSummary,
    summary="Get daily food summary",
)
async def get_daily_summary(
    current_user_id: CurrentUserID,
    date: date = Query(default=None, description="Date (YYYY-MM-DD). Defaults to today."),
) -> DailyFoodSummary:
    """
    Get all food logs and aggregated nutrition for a specific day.
    Defaults to today UTC if no date provided.
    """
    from datetime import datetime, timezone
    target_date = date or datetime.now(timezone.utc).date()
    service = FoodService()
    return await service.get_daily_summary(current_user_id, target_date)


@router.get(
    "/",
    response_model=PaginatedResponse[FoodLogSummary],
    summary="List food logs",
)
async def list_food_logs(
    current_user_id: CurrentUserID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    meal_type: str | None = Query(default=None, description="Filter by meal type"),
    date_from: date | None = Query(default=None, description="Start date filter"),
    date_to: date | None = Query(default=None, description="End date filter"),
) -> PaginatedResponse[FoodLogSummary]:
    """
    List food logs with pagination and optional filtering.
    Results ordered by logged_at descending.
    """
    service = FoodService()
    logs, total = await service.list_logs(
        current_user_id,
        page=page,
        page_size=page_size,
        meal_type=meal_type,
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
    "/{log_id}",
    response_model=FoodLogResponse,
    summary="Get a specific food log",
)
async def get_food_log(
    log_id: UUID,
    current_user_id: CurrentUserID,
) -> FoodLogResponse:
    """Get the full details of a specific food log."""
    service = FoodService()
    return await service.get_log(log_id, current_user_id)


@router.put(
    "/{log_id}",
    response_model=FoodLogResponse,
    summary="Update / correct a food log",
)
async def update_food_log(
    log_id: UUID,
    data: FoodLogUpdate,
    current_user_id: CurrentUserID,
) -> FoodLogResponse:
    """
    Update a food log entry.

    When calories or portion are changed, a correction event is automatically
    recorded to improve future AI estimates.

    Updated entries are marked with `is_corrected: true` and
    `confidence_level: confirmed`.
    """
    service = FoodService()
    return await service.update_log(log_id, current_user_id, data)


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a food log",
)
async def delete_food_log(
    log_id: UUID,
    current_user_id: CurrentUserID,
) -> None:
    """
    Soft delete a food log. The daily summary is automatically updated.
    Hard deletion is only possible via data export/deletion request.
    """
    service = FoodService()
    await service.delete_log(log_id, current_user_id)
