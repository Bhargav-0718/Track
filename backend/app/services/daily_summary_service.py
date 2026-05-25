"""
DailySummaryService — dashboard and Health Connect sync logic.
"""
from datetime import date, datetime, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.repositories.daily_summary_repository import DailySummaryRepository
from app.repositories.food_log_repository import FoodLogRepository
from app.repositories.workout_log_repository import WorkoutLogRepository
from app.schemas.daily_summary import (
    DailySummaryResponse,
    DashboardResponse,
    HealthConnectSyncRequest,
    HealthConnectSyncResponse,
    NutritionTargetProgress,
)
from app.schemas.food_log import FoodLogSummary
from app.schemas.workout_log import WorkoutLogSummary
from app.services.user_service import UserService

logger = get_logger(__name__)


class DailySummaryService:
    def __init__(self) -> None:
        self.summary_repo = DailySummaryRepository()
        self.food_repo = FoodLogRepository()
        self.workout_repo = WorkoutLogRepository()
        self.user_service = UserService()

    async def get_dashboard(
        self,
        user_id: UUID,
        target_date: date | None = None,
    ) -> DashboardResponse:
        """
        Build the full dashboard for a given day.
        Defaults to today UTC if no date provided.
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        # Get or build summary
        summary = await self.summary_repo.get_for_date(user_id, target_date)

        # Get detailed logs for the day
        food_logs = await self.food_repo.get_logs_for_date(user_id, target_date)
        workout_logs = await self.workout_repo.get_logs_for_date(user_id, target_date)

        # Get user's targets for progress calculation
        user = await self.user_service.get_user_by_id(user_id)

        # Build summary from logs if no cached summary exists
        if not summary:
            totals = await self.food_repo.get_daily_nutrition_totals(user_id, target_date)
            workout_totals = await self.workout_repo.get_daily_calories_burned(
                user_id, target_date
            )
            # Build a transient summary (don't persist — it will be created on next log)
            from app.models.daily_summary import DailySummary
            from uuid import uuid4
            summary = DailySummary(
                id=uuid4(),
                user_id=user_id,
                date=target_date,
                total_calories_in=totals["total_calories"],
                total_protein_g=totals["total_protein"],
                total_carbs_g=totals["total_carbs"],
                total_fat_g=totals["total_fat"],
                total_fiber_g=totals["total_fiber"],
                food_log_count=totals["count"],
                total_calories_out=workout_totals["total_calories_burned"],
                workout_count=workout_totals["count"],
                net_calories=totals["total_calories"] - workout_totals["total_calories_burned"],
            )

        # Build progress metrics
        cal_target = user.target_calories
        cal_actual = summary.total_calories_in
        calorie_progress = NutritionTargetProgress(
            target=cal_target,
            actual=cal_actual,
            remaining=max(0.0, cal_target - cal_actual) if cal_target else None,
            percentage=min(100.0, (cal_actual / cal_target * 100)) if cal_target else None,
        )

        protein_target = user.target_protein_g
        protein_actual = summary.total_protein_g
        protein_progress = NutritionTargetProgress(
            target=protein_target,
            actual=protein_actual,
            remaining=max(0.0, protein_target - protein_actual) if protein_target else None,
            percentage=min(100.0, (protein_actual / protein_target * 100)) if protein_target else None,
        )

        return DashboardResponse(
            summary=DailySummaryResponse.model_validate(summary),
            food_logs=[FoodLogSummary.model_validate(log) for log in food_logs],
            workout_logs=[WorkoutLogSummary.model_validate(log) for log in workout_logs],
            calorie_progress=calorie_progress,
            protein_progress=protein_progress,
        )

    async def sync_health_connect(
        self,
        user_id: UUID,
        data: HealthConnectSyncRequest,
    ) -> HealthConnectSyncResponse:
        """
        Receive and store Health Connect data for a specific day.
        Called by the Flutter app after reading from Android Health Connect.
        """
        await self.summary_repo.upsert_health_connect(
            user_id,
            data.date,
            steps=data.steps,
            active_minutes=data.active_minutes,
            activity_calories=data.activity_calories,
        )

        logger.info(
            "health_connect_synced",
            user_id=str(user_id),
            date=str(data.date),
            steps=data.steps,
        )

        return HealthConnectSyncResponse(
            synced=True,
            date=data.date,
            steps=data.steps,
            active_minutes=data.active_minutes,
        )
