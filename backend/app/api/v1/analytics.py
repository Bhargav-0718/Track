"""
Behavioral analytics endpoints.

Routes:
  GET /analytics/summary    → Full behavioral analytics snapshot
  GET /analytics/trend      → Time-series data for Flutter charts
  GET /analytics/streak     → Current streak info only (lightweight)
"""
from fastapi import APIRouter, Query

from app.api.deps import CurrentUserID, DbSession
from app.schemas.analytics import AnalyticsSummary, StreakInfo, TrendResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Full behavioral analytics snapshot",
)
async def get_analytics_summary(
    current_user_id: CurrentUserID,
    db: DbSession,
) -> AnalyticsSummary:
    """
    Complete behavioral analytics for the authenticated user.

    Computed on-demand from existing food logs, workout logs, and checkpoints.
    No separate analytics storage — the logs ARE the behavioral record.

    **Includes**:
    - Current and longest logging streak
    - 7-day and 30-day consistency scores (logging, calories, protein, workouts)
    - Meal pattern analysis (which meals you log most/least)
    - AI estimation accuracy (how often you correct the AI)
    - Pattern insights (heuristic sentences, not ML)
    - Weight trend from progress checkpoints

    Use this data to populate the Flutter analytics dashboard.
    Response is computed live — cache on the client for 15-30 minutes.
    """
    service = AnalyticsService(db)
    return await service.get_summary(current_user_id)


@router.get(
    "/trend",
    response_model=TrendResponse,
    summary="Time-series trend data for charts",
)
async def get_trend(
    current_user_id: CurrentUserID,
    db: DbSession,
    period_days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Number of days to include in the trend (7, 14, 30, or 90)"
    ),
) -> TrendResponse:
    """
    Daily time-series data for calorie, protein, and workout trend charts.

    Returns one data point per day for the last `period_days` days.
    Days with no logs have calories=0 and logged=false.

    **Usage in Flutter**: Feed directly into fl_chart line charts.
    The `calorie_target` field can be used to render a horizontal target line.
    """
    service = AnalyticsService(db)
    return await service.get_trend(current_user_id, period_days=period_days)


@router.get(
    "/streak",
    response_model=StreakInfo,
    summary="Current logging streak (lightweight)",
)
async def get_streak(
    current_user_id: CurrentUserID,
    db: DbSession,
) -> StreakInfo:
    """
    Get current and longest logging streak.
    Lightweight endpoint — use for home screen widgets and streak badges.
    For full analytics, use GET /analytics/summary.
    """
    from datetime import date
    service = AnalyticsService(db)
    return await service._compute_streak(current_user_id, date.today())
