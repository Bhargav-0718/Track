"""
FoodLog repository — all Beanie queries for food log data access.
"""
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from uuid import UUID

from app.models.food_log import FoodLog
from app.repositories.base import BaseRepository


class FoodLogRepository(BaseRepository[FoodLog]):
    def __init__(self) -> None:
        super().__init__(FoodLog)

    async def get_logs_for_date(
        self,
        user_id: UUID,
        target_date: date,
        *,
        include_deleted: bool = False,
    ) -> list[FoodLog]:
        """Get all food logs for a user on a specific date."""
        day_start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=dt_timezone.utc
        )
        day_end = day_start + timedelta(days=1)

        filters = [
            FoodLog.user_id == user_id,
            FoodLog.logged_at >= day_start,
            FoodLog.logged_at < day_end,
        ]
        if not include_deleted:
            filters.append(FoodLog.is_deleted == False)  # noqa: E712

        return await FoodLog.find(*filters).sort(FoodLog.logged_at).to_list()

    async def get_logs_paginated(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        meal_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[FoodLog], int]:
        """Paginated food logs with optional filters. Returns (logs, total_count)."""
        filters = [
            FoodLog.user_id == user_id,
            FoodLog.is_deleted == False,  # noqa: E712
        ]

        if meal_type:
            filters.append(FoodLog.meal_type == meal_type)

        if date_from:
            day_start = datetime.combine(date_from, datetime.min.time()).replace(
                tzinfo=dt_timezone.utc
            )
            filters.append(FoodLog.logged_at >= day_start)

        if date_to:
            day_end = datetime.combine(date_to, datetime.max.time()).replace(
                tzinfo=dt_timezone.utc
            )
            filters.append(FoodLog.logged_at <= day_end)

        query = FoodLog.find(*filters)
        total = await query.count()

        offset = (page - 1) * page_size
        logs = await query.sort(-FoodLog.logged_at).skip(offset).limit(page_size).to_list()

        return logs, total

    async def get_daily_nutrition_totals(
        self,
        user_id: UUID,
        target_date: date,
    ) -> dict:
        """Aggregate nutrition totals for a given day (Python-side aggregation)."""
        logs = await self.get_logs_for_date(user_id, target_date)

        total_calories = sum(log.calories for log in logs)
        total_protein = sum(log.protein_g or 0.0 for log in logs)
        total_carbs = sum(log.carbs_g or 0.0 for log in logs)
        total_fat = sum(log.fat_g or 0.0 for log in logs)
        total_fiber = sum(log.fiber_g or 0.0 for log in logs)

        return {
            "total_calories": round(total_calories, 2),
            "total_protein": round(total_protein, 2),
            "total_carbs": round(total_carbs, 2),
            "total_fat": round(total_fat, 2),
            "total_fiber": round(total_fiber, 2),
            "count": len(logs),
        }

    async def create_food_log(
        self,
        user_id: UUID,
        food_name: str,
        calories: float,
        *,
        raw_input: str | None = None,
        brand_name: str | None = None,
        meal_type: str = "snack",
        portion_description: str | None = None,
        portion_grams: float | None = None,
        protein_g: float | None = None,
        carbs_g: float | None = None,
        fat_g: float | None = None,
        fiber_g: float | None = None,
        estimation_source: str = "manual",
        confidence_score: float = 1.0,
        confidence_level: str = "confirmed",
        assumptions: list[str] | None = None,
        logged_at: datetime | None = None,
        nutrition_cache_id: UUID | None = None,
        memory_id: UUID | None = None,
    ) -> FoodLog:
        """Create a new food log document."""
        log = FoodLog(
            user_id=user_id,
            food_name=food_name,
            calories=calories,
            raw_input=raw_input,
            brand_name=brand_name,
            meal_type=meal_type,
            portion_description=portion_description,
            portion_grams=portion_grams,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            fiber_g=fiber_g,
            estimation_source=estimation_source,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            assumptions=assumptions or [],
            logged_at=logged_at or datetime.now(dt_timezone.utc),
            nutrition_cache_id=nutrition_cache_id,
            memory_id=memory_id,
        )
        await log.insert()
        return log

    async def mark_corrected(
        self,
        log: FoodLog,
        *,
        new_calories: float | None = None,
        new_portion_grams: float | None = None,
        new_food_name: str | None = None,
        new_meal_type: str | None = None,
        new_protein_g: float | None = None,
        new_carbs_g: float | None = None,
        new_fat_g: float | None = None,
        new_fiber_g: float | None = None,
        new_portion_description: str | None = None,
    ) -> FoodLog:
        """Apply user corrections to a food log."""
        if new_calories is not None and not log.is_corrected:
            log.original_calories = log.calories
        if new_portion_grams is not None and not log.is_corrected:
            log.original_portion_grams = log.portion_grams

        if new_calories is not None:
            log.calories = new_calories
        if new_portion_grams is not None:
            log.portion_grams = new_portion_grams
        if new_food_name is not None:
            log.food_name = new_food_name
        if new_meal_type is not None:
            log.meal_type = new_meal_type
        if new_protein_g is not None:
            log.protein_g = new_protein_g
        if new_carbs_g is not None:
            log.carbs_g = new_carbs_g
        if new_fat_g is not None:
            log.fat_g = new_fat_g
        if new_fiber_g is not None:
            log.fiber_g = new_fiber_g
        if new_portion_description is not None:
            log.portion_description = new_portion_description

        log.is_corrected = True
        log.confidence_score = 1.0
        log.confidence_level = "confirmed"
        log.updated_at = datetime.now(dt_timezone.utc)

        await log.save()
        return log

    async def get_recent_foods(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        days_back: int = 30,
    ) -> list[FoodLog]:
        """
        Get recently logged foods, deduped by food_name (most recent per food).
        """
        cutoff = datetime.now(dt_timezone.utc) - timedelta(days=days_back)

        logs = await FoodLog.find(
            FoodLog.user_id == user_id,
            FoodLog.logged_at >= cutoff,
            FoodLog.is_deleted == False,  # noqa: E712
        ).sort(-FoodLog.logged_at).to_list()

        # Deduplicate by food_name keeping the most recent (list is already sorted)
        seen: set[str] = set()
        deduped: list[FoodLog] = []
        for log in logs:
            key = log.food_name.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(log)
            if len(deduped) >= limit:
                break

        return deduped
