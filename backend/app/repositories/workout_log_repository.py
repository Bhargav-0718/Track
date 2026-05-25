"""
WorkoutLog repository.
"""
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from uuid import UUID

from app.models.workout_log import WorkoutLog
from app.repositories.base import BaseRepository


class WorkoutLogRepository(BaseRepository[WorkoutLog]):
    def __init__(self) -> None:
        super().__init__(WorkoutLog)

    async def get_logs_for_date(
        self,
        user_id: UUID,
        target_date: date,
    ) -> list[WorkoutLog]:
        """Get all workouts for a user on a specific date."""
        day_start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=dt_timezone.utc
        )
        day_end = day_start + timedelta(days=1)

        return await WorkoutLog.find(
            WorkoutLog.user_id == user_id,
            WorkoutLog.logged_at >= day_start,
            WorkoutLog.logged_at < day_end,
            WorkoutLog.is_deleted == False,  # noqa: E712
        ).sort(WorkoutLog.logged_at).to_list()

    async def get_logs_paginated(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        workout_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[WorkoutLog], int]:
        """Paginated workout logs with optional filters."""
        filters = [
            WorkoutLog.user_id == user_id,
            WorkoutLog.is_deleted == False,  # noqa: E712
        ]

        if workout_type:
            filters.append(WorkoutLog.workout_type == workout_type)

        if date_from:
            day_start = datetime.combine(date_from, datetime.min.time()).replace(
                tzinfo=dt_timezone.utc
            )
            filters.append(WorkoutLog.logged_at >= day_start)

        if date_to:
            day_end = datetime.combine(date_to, datetime.max.time()).replace(
                tzinfo=dt_timezone.utc
            )
            filters.append(WorkoutLog.logged_at <= day_end)

        query = WorkoutLog.find(*filters)
        total = await query.count()
        offset = (page - 1) * page_size
        logs = await query.sort(-WorkoutLog.logged_at).skip(offset).limit(page_size).to_list()
        return logs, total

    async def get_daily_calories_burned(
        self,
        user_id: UUID,
        target_date: date,
    ) -> dict:
        """Sum calories burned from workouts for a given day."""
        logs = await self.get_logs_for_date(user_id, target_date)
        return {
            "total_calories_burned": sum(log.calories_burned or 0.0 for log in logs),
            "total_minutes": sum(log.duration_minutes for log in logs),
            "count": len(logs),
        }

    async def health_connect_id_exists(self, health_connect_id: str) -> bool:
        """Check if a Health Connect workout ID has already been synced."""
        result = await WorkoutLog.find_one(
            WorkoutLog.health_connect_id == health_connect_id
        )
        return result is not None

    async def get_by_health_connect_id(self, health_connect_id: str) -> WorkoutLog | None:
        """Fetch existing workout by Health Connect ID."""
        return await WorkoutLog.find_one(
            WorkoutLog.health_connect_id == health_connect_id
        )

    async def create_workout_log(
        self,
        user_id: UUID,
        title: str,
        workout_type: str,
        duration_minutes: int,
        *,
        intensity: str = "moderate",
        calories_burned: float | None = None,
        calories_source: str = "manual",
        exercises: list | None = None,
        notes: str | None = None,
        raw_input: str | None = None,
        logged_at: datetime | None = None,
        health_connect_id: str | None = None,
    ) -> WorkoutLog:
        """Create a new workout log document."""
        log = WorkoutLog(
            user_id=user_id,
            title=title,
            workout_type=workout_type,
            duration_minutes=duration_minutes,
            intensity=intensity,
            calories_burned=calories_burned,
            calories_source=calories_source,
            exercises=exercises or [],
            notes=notes,
            raw_input=raw_input,
            logged_at=logged_at or datetime.now(dt_timezone.utc),
            health_connect_id=health_connect_id,
        )
        await log.insert()
        return log

    async def get_by_id_for_user(self, id: UUID, user_id: UUID) -> WorkoutLog | None:
        return await WorkoutLog.find_one(
            WorkoutLog.id == id,
            WorkoutLog.user_id == user_id,
        )
