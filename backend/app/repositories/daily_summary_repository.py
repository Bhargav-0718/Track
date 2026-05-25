"""
DailySummary repository — upsert-heavy operations for maintaining daily aggregates.
"""
from datetime import date, datetime
from datetime import timezone as dt_timezone
from uuid import UUID

from app.models.daily_summary import DailySummary
from app.repositories.base import BaseRepository


class DailySummaryRepository(BaseRepository[DailySummary]):
    def __init__(self) -> None:
        super().__init__(DailySummary)

    async def get_for_date(
        self,
        user_id: UUID,
        target_date: date,
    ) -> DailySummary | None:
        """Get the daily summary for a specific user and date."""
        return await DailySummary.find_one(
            DailySummary.user_id == user_id,
            DailySummary.date == target_date,
        )

    async def get_range(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[DailySummary]:
        """Get daily summaries for a date range (inclusive)."""
        all_summaries = await DailySummary.find(
            DailySummary.user_id == user_id,
        ).to_list()
        return [
            s for s in all_summaries
            if date_from <= s.date <= date_to
        ]

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
        """Upsert nutrition totals for a day."""
        existing = await self.get_for_date(user_id, target_date)

        if existing:
            existing.total_calories_in = total_calories_in
            existing.total_protein_g = total_protein_g
            existing.total_carbs_g = total_carbs_g
            existing.total_fat_g = total_fat_g
            existing.total_fiber_g = total_fiber_g
            existing.food_log_count = food_log_count
            existing.net_calories = total_calories_in - existing.total_calories_out
            existing.updated_at = datetime.now(dt_timezone.utc)
            await existing.save()
            return existing
        else:
            summary = DailySummary(
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
            await summary.insert()
            return summary

    async def upsert_workout(
        self,
        user_id: UUID,
        target_date: date,
        *,
        total_calories_out: float,
        workout_count: int,
    ) -> DailySummary:
        """Upsert workout totals for a day."""
        existing = await self.get_for_date(user_id, target_date)

        if existing:
            existing.total_calories_out = total_calories_out
            existing.workout_count = workout_count
            existing.net_calories = existing.total_calories_in - total_calories_out
            existing.updated_at = datetime.now(dt_timezone.utc)
            await existing.save()
            return existing
        else:
            summary = DailySummary(
                user_id=user_id,
                date=target_date,
                total_calories_out=total_calories_out,
                workout_count=workout_count,
                net_calories=-total_calories_out,
            )
            await summary.insert()
            return summary

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
        existing = await self.get_for_date(user_id, target_date)

        if existing:
            if steps is not None:
                existing.steps = steps
            if active_minutes is not None:
                existing.active_minutes = active_minutes
            if activity_calories is not None:
                existing.activity_calories = activity_calories
            existing.health_connect_synced = True
            existing.last_synced_at = datetime.now(dt_timezone.utc)
            existing.updated_at = datetime.now(dt_timezone.utc)
            await existing.save()
            return existing
        else:
            summary = DailySummary(
                user_id=user_id,
                date=target_date,
                steps=steps,
                active_minutes=active_minutes,
                activity_calories=activity_calories,
                health_connect_synced=True,
                last_synced_at=datetime.now(dt_timezone.utc),
            )
            await summary.insert()
            return summary
