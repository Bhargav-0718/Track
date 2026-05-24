"""
WorkoutLog repository.
"""
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workout_log import WorkoutLog
from app.repositories.base import BaseRepository


class WorkoutLogRepository(BaseRepository[WorkoutLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WorkoutLog, session)

    async def get_logs_for_date(
        self,
        user_id: UUID,
        target_date: date,
    ) -> list[WorkoutLog]:
        """Get all workouts for a user on a specific date."""
        day_start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        day_end = day_start + timedelta(days=1)

        result = await self.session.execute(
            select(WorkoutLog).where(
                and_(
                    WorkoutLog.user_id == user_id,
                    WorkoutLog.logged_at >= day_start,
                    WorkoutLog.logged_at < day_end,
                    WorkoutLog.is_deleted.is_(False),
                )
            ).order_by(WorkoutLog.logged_at)
        )
        return list(result.scalars().all())

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
        base_filter = and_(
            WorkoutLog.user_id == user_id,
            WorkoutLog.is_deleted.is_(False),
        )

        if workout_type:
            base_filter = and_(base_filter, WorkoutLog.workout_type == workout_type)

        if date_from:
            day_start = datetime.combine(date_from, datetime.min.time()).replace(
                tzinfo=timezone.utc
            )
            base_filter = and_(base_filter, WorkoutLog.logged_at >= day_start)

        if date_to:
            day_end = datetime.combine(date_to, datetime.max.time()).replace(
                tzinfo=timezone.utc
            )
            base_filter = and_(base_filter, WorkoutLog.logged_at <= day_end)

        count_result = await self.session.execute(
            select(func.count()).select_from(WorkoutLog).where(base_filter)
        )
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        data_result = await self.session.execute(
            select(WorkoutLog)
            .where(base_filter)
            .order_by(desc(WorkoutLog.logged_at))
            .limit(page_size)
            .offset(offset)
        )
        return list(data_result.scalars().all()), total

    async def get_daily_calories_burned(
        self,
        user_id: UUID,
        target_date: date,
    ) -> dict:
        """Sum calories burned from workouts for a given day."""
        day_start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        day_end = day_start + timedelta(days=1)

        result = await self.session.execute(
            select(
                func.coalesce(func.sum(WorkoutLog.calories_burned), 0.0).label("total_burned"),
                func.coalesce(func.sum(WorkoutLog.duration_minutes), 0).label("total_minutes"),
                func.count(WorkoutLog.id).label("count"),
            ).where(
                and_(
                    WorkoutLog.user_id == user_id,
                    WorkoutLog.logged_at >= day_start,
                    WorkoutLog.logged_at < day_end,
                    WorkoutLog.is_deleted.is_(False),
                )
            )
        )
        row = result.one()
        return {
            "total_calories_burned": float(row.total_burned),
            "total_minutes": int(row.total_minutes),
            "count": int(row.count),
        }

    async def health_connect_id_exists(
        self,
        health_connect_id: str,
    ) -> bool:
        """Check if a Health Connect workout ID has already been synced."""
        result = await self.session.execute(
            select(WorkoutLog.id).where(
                WorkoutLog.health_connect_id == health_connect_id
            )
        )
        return result.scalar_one_or_none() is not None

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
        """Create a new workout log."""
        return await self.create(
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
            logged_at=logged_at or datetime.now(timezone.utc),
            health_connect_id=health_connect_id,
        )
