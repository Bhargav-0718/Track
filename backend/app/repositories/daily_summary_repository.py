"""
DailySummary repository — upsert-heavy operations for maintaining daily aggregates.
"""
from datetime import date
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_summary import DailySummary
from app.repositories.base import BaseRepository


class DailySummaryRepository(BaseRepository[DailySummary]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DailySummary, session)

    async def get_for_date(
        self,
        user_id: UUID,
        target_date: date,
    ) -> DailySummary | None:
        """Get the daily summary for a specific user and date."""
        result = await self.session.execute(
            select(DailySummary).where(
                and_(
                    DailySummary.user_id == user_id,
                    DailySummary.date == target_date,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_range(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[DailySummary]:
        """Get daily summaries for a date range (inclusive)."""
        result = await self.session.execute(
            select(DailySummary)
            .where(
                and_(
                    DailySummary.user_id == user_id,
                    DailySummary.date >= date_from,
                    DailySummary.date <= date_to,
                )
            )
            .order_by(DailySummary.date)
        )
        return list(result.scalars().all())

    async def upsert_nutrition(
        self,
        user_id: UUID,
        target_date: date,
        *,
        total_calories_in: float,
        total_protein_g: float,
        total_carbs_g: float,
        total_fat_g: float,
        total_fiber_g: float,
        food_log_count: int,
    ) -> DailySummary:
        """
        Upsert nutrition totals for a day.
        Called after every food log create/update/delete.
        """
        existing = await self.get_for_date(user_id, target_date)

        if existing:
            existing.total_calories_in = total_calories_in
            existing.total_protein_g = total_protein_g
            existing.total_carbs_g = total_carbs_g
            existing.total_fat_g = total_fat_g
            existing.total_fiber_g = total_fiber_g
            existing.food_log_count = food_log_count
            # Recompute net
            existing.net_calories = total_calories_in - existing.total_calories_out
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            return await self.create(
                user_id=user_id,
                date=target_date,
                total_calories_in=total_calories_in,
                total_protein_g=total_protein_g,
                total_carbs_g=total_carbs_g,
                total_fat_g=total_fat_g,
                total_fiber_g=total_fiber_g,
                food_log_count=food_log_count,
                net_calories=total_calories_in,
            )

    async def upsert_workout(
        self,
        user_id: UUID,
        target_date: date,
        *,
        total_calories_out: float,
        workout_count: int,
    ) -> DailySummary:
        """
        Upsert workout totals for a day.
        Called after every workout log create/update/delete.
        """
        existing = await self.get_for_date(user_id, target_date)

        if existing:
            existing.total_calories_out = total_calories_out
            existing.workout_count = workout_count
            existing.net_calories = existing.total_calories_in - total_calories_out
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            return await self.create(
                user_id=user_id,
                date=target_date,
                total_calories_out=total_calories_out,
                workout_count=workout_count,
                net_calories=-total_calories_out,
            )

    async def upsert_health_connect(
        self,
        user_id: UUID,
        target_date: date,
        *,
        steps: int | None,
        active_minutes: int | None,
        activity_calories: float | None,
    ) -> DailySummary:
        """Update Health Connect data for a day."""
        from datetime import datetime, timezone
        existing = await self.get_for_date(user_id, target_date)

        if existing:
            if steps is not None:
                existing.steps = steps
            if active_minutes is not None:
                existing.active_minutes = active_minutes
            if activity_calories is not None:
                existing.activity_calories = activity_calories
            existing.health_connect_synced = True
            existing.last_synced_at = datetime.now(timezone.utc)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            return await self.create(
                user_id=user_id,
                date=target_date,
                steps=steps,
                active_minutes=active_minutes,
                activity_calories=activity_calories,
                health_connect_synced=True,
            )
