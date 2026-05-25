"""
WorkoutService — business logic for workout tracking.
"""
from datetime import date, datetime
from datetime import timezone as dt_timezone
from uuid import UUID

from app.core.exceptions import ResourceNotFoundError
from app.core.logging import get_logger
from app.models.workout_log import WorkoutLog
from app.repositories.daily_summary_repository import DailySummaryRepository
from app.repositories.workout_log_repository import WorkoutLogRepository
from app.schemas.workout_log import (
    WorkoutLogCreate,
    WorkoutLogResponse,
    WorkoutLogSummary,
    WorkoutLogUpdate,
)

logger = get_logger(__name__)

MET_VALUES: dict[str, dict[str, float]] = {
    "cardio": {"low": 5.0, "moderate": 7.0, "high": 10.0, "very_high": 14.0},
    "strength": {"low": 3.0, "moderate": 5.0, "high": 6.0, "very_high": 8.0},
    "hiit": {"low": 7.0, "moderate": 9.0, "high": 12.0, "very_high": 15.0},
    "yoga": {"low": 2.5, "moderate": 3.5, "high": 4.0, "very_high": 5.0},
    "sports": {"low": 5.0, "moderate": 7.0, "high": 10.0, "very_high": 12.0},
    "other": {"low": 3.0, "moderate": 5.0, "high": 7.0, "very_high": 9.0},
}
DEFAULT_WEIGHT_KG = 70.0


def estimate_calories_burned(
    workout_type: str,
    intensity: str,
    duration_minutes: int,
    weight_kg: float = DEFAULT_WEIGHT_KG,
) -> tuple[float, str]:
    met = MET_VALUES.get(workout_type, MET_VALUES["other"]).get(intensity, 5.0)
    calories = met * weight_kg * (duration_minutes / 60)
    return round(calories, 1), "formula"


class WorkoutService:
    def __init__(self) -> None:
        self.workout_repo = WorkoutLogRepository()
        self.summary_repo = DailySummaryRepository()

    async def create_log(
        self,
        user_id: UUID,
        data: WorkoutLogCreate,
        *,
        user_weight_kg: float | None = None,
    ) -> WorkoutLogResponse:
        if data.calories_burned is not None:
            calories_burned = data.calories_burned
            calories_source = "health_connect" if data.health_connect_id else "manual"
        else:
            weight = user_weight_kg or DEFAULT_WEIGHT_KG
            calories_burned, calories_source = estimate_calories_burned(
                workout_type=data.workout_type,
                intensity=data.intensity,
                duration_minutes=data.duration_minutes,
                weight_kg=weight,
            )

        if data.health_connect_id:
            if await self.workout_repo.health_connect_id_exists(data.health_connect_id):
                logger.info("health_connect_workout_duplicate", id=data.health_connect_id)
                existing = await self.workout_repo.get_by_health_connect_id(data.health_connect_id)
                if existing:
                    return WorkoutLogResponse.model_validate(existing)

        log = await self.workout_repo.create_workout_log(
            user_id=user_id,
            title=data.title,
            workout_type=data.workout_type,
            duration_minutes=data.duration_minutes,
            intensity=data.intensity,
            calories_burned=calories_burned,
            calories_source=calories_source,
            exercises=[ex.model_dump() for ex in data.exercises],
            notes=data.notes,
            raw_input=data.raw_input,
            logged_at=data.logged_at or datetime.now(dt_timezone.utc),
            health_connect_id=data.health_connect_id,
        )

        await self._refresh_daily_summary(user_id, log.logged_at.date())

        logger.info(
            "workout_logged",
            user_id=str(user_id),
            type=data.workout_type,
            duration=data.duration_minutes,
            calories=calories_burned,
        )

        return WorkoutLogResponse.model_validate(log)

    async def get_log(self, log_id: UUID, user_id: UUID) -> WorkoutLogResponse:
        log = await self.workout_repo.get_by_id_for_user(log_id, user_id)
        if not log or log.is_deleted:
            raise ResourceNotFoundError(
                message=f"Workout log {log_id} not found",
                resource_type="WorkoutLog",
                resource_id=str(log_id),
            )
        return WorkoutLogResponse.model_validate(log)

    async def update_log(
        self,
        log_id: UUID,
        user_id: UUID,
        data: WorkoutLogUpdate,
        *,
        user_weight_kg: float | None = None,
    ) -> WorkoutLogResponse:
        log = await self.workout_repo.get_by_id_for_user(log_id, user_id)
        if not log or log.is_deleted:
            raise ResourceNotFoundError(
                message=f"Workout log {log_id} not found",
                resource_type="WorkoutLog",
                resource_id=str(log_id),
            )

        original_date = log.logged_at.date()

        if data.title is not None:
            log.title = data.title
        if data.workout_type is not None:
            log.workout_type = data.workout_type
        if data.duration_minutes is not None:
            log.duration_minutes = data.duration_minutes
        if data.intensity is not None:
            log.intensity = data.intensity
        if data.notes is not None:
            log.notes = data.notes
        if data.exercises is not None:
            log.exercises = [ex.model_dump() for ex in data.exercises]
        if data.logged_at is not None:
            log.logged_at = data.logged_at

        if data.calories_burned is not None:
            log.calories_burned = data.calories_burned
            log.calories_source = "manual"
        elif any([data.workout_type, data.duration_minutes, data.intensity]):
            if log.calories_source == "formula":
                weight = user_weight_kg or DEFAULT_WEIGHT_KG
                new_cal, source = estimate_calories_burned(
                    workout_type=log.workout_type,
                    intensity=log.intensity,
                    duration_minutes=log.duration_minutes,
                    weight_kg=weight,
                )
                log.calories_burned = new_cal
                log.calories_source = source

        log.updated_at = datetime.now(dt_timezone.utc)
        await log.save()

        await self._refresh_daily_summary(user_id, original_date)
        if data.logged_at and data.logged_at.date() != original_date:
            await self._refresh_daily_summary(user_id, data.logged_at.date())

        return WorkoutLogResponse.model_validate(log)

    async def delete_log(self, log_id: UUID, user_id: UUID) -> None:
        log = await self.workout_repo.get_by_id_for_user(log_id, user_id)
        if not log or log.is_deleted:
            raise ResourceNotFoundError(
                message=f"Workout log {log_id} not found",
                resource_type="WorkoutLog",
                resource_id=str(log_id),
            )
        target_date = log.logged_at.date()
        await self.workout_repo.soft_delete(log)
        await self._refresh_daily_summary(user_id, target_date)

    async def list_logs(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        workout_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[WorkoutLogSummary], int]:
        logs, total = await self.workout_repo.get_logs_paginated(
            user_id,
            page=page,
            page_size=page_size,
            workout_type=workout_type,
            date_from=date_from,
            date_to=date_to,
        )
        return [WorkoutLogSummary.model_validate(log) for log in logs], total

    async def _refresh_daily_summary(self, user_id: UUID, target_date: date) -> None:
        totals = await self.workout_repo.get_daily_calories_burned(user_id, target_date)
        await self.summary_repo.upsert_workout(
            user_id,
            target_date,
            total_calories_out=totals["total_calories_burned"],
            workout_count=totals["count"],
        )
