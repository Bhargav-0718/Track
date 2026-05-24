"""
FoodService — business logic for food logging.

Phase 2: Full AI estimation pipeline active.
- Quick log (raw_input only) → EstimationService → memory+DB+LLM pipeline
- Manual log (explicit nutrition) → stored directly, confidence=confirmed
- Every log updates food_memory (the continuous learning layer)
- Every correction records a CorrectionEvent + updates food_memory

The AI pipeline (EstimationService) is invoked only for quick_log mode.
Manual entries are trusted as-is — the user knows best.
"""
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.core.logging import get_logger
from app.models.food_log import FoodLog
from app.repositories.daily_summary_repository import DailySummaryRepository
from app.repositories.food_log_repository import FoodLogRepository
from app.repositories.food_memory_repository import FoodMemoryRepository
from app.schemas.common import ConfidenceLevel, EstimationSource
from app.schemas.food_log import (
    DailyFoodSummary,
    FoodLogCreate,
    FoodLogResponse,
    FoodLogSummary,
    FoodLogUpdate,
)
from app.services.estimation_service import EstimationResult, EstimationService

logger = get_logger(__name__)


class FoodService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.food_repo = FoodLogRepository(session)
        self.summary_repo = DailySummaryRepository(session)
        self.memory_repo = FoodMemoryRepository(session)

    # ── Core CRUD ──────────────────────────────────────────────────────────────

    async def create_log(
        self,
        user_id: UUID,
        data: FoodLogCreate,
    ) -> FoodLogResponse:
        """
        Create a food log entry.

        Quick log (raw_input):
          → EstimationService runs memory → DB → LLM pipeline
          → Automatically estimates nutrition with confidence scoring
          → Updates food_memory for future faster lookups

        Manual log (food_name + calories):
          → Stored directly, confidence=confirmed
          → Still updates food_memory (user-provided data is valuable)
        """
        if data.is_quick_log:
            log = await self._create_quick_log(user_id, data)
        else:
            log = await self._create_manual_log(user_id, data)

        # Update food memory after every successful log
        await self._update_memory(user_id, log, is_correction=False)

        await self._refresh_daily_summary(user_id, log.logged_at.date())
        await self.session.commit()

        logger.info(
            "food_logged",
            user_id=str(user_id),
            food=log.food_name,
            calories=log.calories,
            source=log.estimation_source,
            confidence=log.confidence_score,
        )

        return FoodLogResponse.model_validate(log)

    async def _create_quick_log(
        self,
        user_id: UUID,
        data: FoodLogCreate,
    ) -> FoodLog:
        """
        Quick log path: run the full estimation pipeline on raw_input.
        If estimation fails gracefully, fall back to creating an uncertain entry.
        """
        try:
            estimator = EstimationService(self.session)
            result: EstimationResult = await estimator.estimate(
                raw_input=data.raw_input or "",
                user_id=user_id,
            )
        except Exception as e:
            logger.warning("estimation_pipeline_failed", error=str(e), raw=data.raw_input)
            # Graceful degradation — never fail the log creation
            return await self.food_repo.create_food_log(
                user_id=user_id,
                food_name=data.raw_input or "Unknown",
                calories=0.0,
                raw_input=data.raw_input,
                meal_type=data.meal_type,
                estimation_source=EstimationSource.MANUAL,
                confidence_score=0.0,
                confidence_level=ConfidenceLevel.UNCERTAIN,
                assumptions=["Estimation failed — please edit to add nutrition values"],
                logged_at=data.logged_at or datetime.now(timezone.utc),
            )

        return await self.food_repo.create_food_log(
            user_id=user_id,
            food_name=result.food_name,
            calories=result.calories,
            raw_input=data.raw_input,
            meal_type=data.meal_type,
            portion_description=result.portion_description,
            portion_grams=result.portion_grams,
            protein_g=result.protein_g,
            carbs_g=result.carbs_g,
            fat_g=result.fat_g,
            fiber_g=result.fiber_g,
            estimation_source=result.estimation_source,
            confidence_score=result.confidence_score,
            confidence_level=result.confidence_level,
            assumptions=result.assumptions,
            logged_at=data.logged_at or datetime.now(timezone.utc),
            nutrition_cache_id=result.nutrition_cache_id,
            memory_id=result.memory_id,
        )

    async def _create_manual_log(
        self,
        user_id: UUID,
        data: FoodLogCreate,
    ) -> FoodLog:
        """Manual log: user provides explicit values. Trust them completely."""
        return await self.food_repo.create_food_log(
            user_id=user_id,
            food_name=data.food_name or "Unknown Food",
            calories=data.calories or 0.0,
            raw_input=data.raw_input,
            brand_name=data.brand_name,
            meal_type=data.meal_type,
            portion_description=data.portion_description,
            portion_grams=data.portion_grams,
            protein_g=data.protein_g,
            carbs_g=data.carbs_g,
            fat_g=data.fat_g,
            fiber_g=data.fiber_g,
            estimation_source=EstimationSource.MANUAL,
            confidence_score=1.0,
            confidence_level=ConfidenceLevel.CONFIRMED,
            assumptions=[],
            logged_at=data.logged_at or datetime.now(timezone.utc),
        )

    async def get_log(
        self,
        log_id: UUID,
        user_id: UUID,
    ) -> FoodLogResponse:
        log = await self.food_repo.get_by_id_for_user(log_id, user_id)
        if not log or log.is_deleted:
            raise ResourceNotFoundError(
                message=f"Food log {log_id} not found",
                resource_type="FoodLog",
                resource_id=str(log_id),
            )
        return FoodLogResponse.model_validate(log)

    async def update_log(
        self,
        log_id: UUID,
        user_id: UUID,
        data: FoodLogUpdate,
    ) -> FoodLogResponse:
        """
        Update a food log — user correction.

        On calorie/portion change:
        1. Store original values (for delta analysis)
        2. Mark is_corrected=True, confidence=confirmed
        3. Record CorrectionEvent (Phase 4 signal)
        4. Update food_memory with correction weight (3× normal weight)
        5. Refresh daily summary
        """
        log = await self.food_repo.get_by_id_for_user(log_id, user_id)
        if not log or log.is_deleted:
            raise ResourceNotFoundError(
                message=f"Food log {log_id} not found",
                resource_type="FoodLog",
                resource_id=str(log_id),
            )

        original_calories = log.calories
        original_portion = log.portion_grams
        original_logged_at = log.logged_at

        updated_log = await self.food_repo.mark_corrected(
            log,
            new_calories=data.calories,
            new_portion_grams=data.portion_grams,
            new_food_name=data.food_name,
            new_meal_type=data.meal_type,
            new_protein_g=data.protein_g,
            new_carbs_g=data.carbs_g,
            new_fat_g=data.fat_g,
            new_fiber_g=data.fiber_g,
            new_portion_description=data.portion_description,
        )

        # Record correction event if calories changed
        if data.calories is not None and data.calories != original_calories:
            await self._record_correction(
                user_id=user_id,
                log_id=log_id,
                correction_type="calories",
                original_value=original_calories,
                corrected_value=data.calories,
                original_source=log.estimation_source,
                original_confidence=log.confidence_score,
            )

        # Update food memory with corrected values (high-weight update)
        await self._update_memory(user_id, updated_log, is_correction=True)

        target_date = (data.logged_at or original_logged_at).date()
        await self._refresh_daily_summary(user_id, target_date)
        await self.session.commit()

        logger.info(
            "food_log_corrected",
            log_id=str(log_id),
            user_id=str(user_id),
            old_cal=original_calories,
            new_cal=data.calories,
        )

        return FoodLogResponse.model_validate(updated_log)

    async def delete_log(self, log_id: UUID, user_id: UUID) -> None:
        log = await self.food_repo.get_by_id_for_user(log_id, user_id)
        if not log or log.is_deleted:
            raise ResourceNotFoundError(
                message=f"Food log {log_id} not found",
                resource_type="FoodLog",
                resource_id=str(log_id),
            )
        target_date = log.logged_at.date()
        await self.food_repo.soft_delete(log)
        await self._refresh_daily_summary(user_id, target_date)
        await self.session.commit()

    # ── List + Summary ─────────────────────────────────────────────────────────

    async def list_logs(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        meal_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[FoodLogSummary], int]:
        logs, total = await self.food_repo.get_logs_paginated(
            user_id,
            page=page,
            page_size=page_size,
            meal_type=meal_type,
            date_from=date_from,
            date_to=date_to,
        )
        return [FoodLogSummary.model_validate(log) for log in logs], total

    async def get_daily_summary(
        self,
        user_id: UUID,
        target_date: date,
    ) -> DailyFoodSummary:
        logs = await self.food_repo.get_logs_for_date(user_id, target_date)
        totals = await self.food_repo.get_daily_nutrition_totals(user_id, target_date)
        return DailyFoodSummary(
            date=target_date.isoformat(),
            total_calories=totals["total_calories"],
            total_protein_g=totals["total_protein"],
            total_carbs_g=totals["total_carbs"],
            total_fat_g=totals["total_fat"],
            food_count=totals["count"],
            logs=[FoodLogSummary.model_validate(log) for log in logs],
        )

    async def get_recent_foods(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[FoodLogSummary]:
        logs = await self.food_repo.get_recent_foods(user_id, limit=limit)
        return [FoodLogSummary.model_validate(log) for log in logs]

    # ── Internal Helpers ───────────────────────────────────────────────────────

    async def _update_memory(
        self,
        user_id: UUID,
        log: FoodLog,
        is_correction: bool,
    ) -> None:
        """
        Update food_memory after a log is created or corrected.
        This is the "continuous learning" mechanism.
        """
        if not log.food_name or log.calories == 0:
            return

        try:
            # Get embedding for memory update (async, non-blocking)
            from app.services.ai.embedding_service import embed_text
            embedding = await embed_text(log.food_name)
        except Exception as e:
            logger.warning("embedding_failed_for_memory_update", error=str(e))
            embedding = None

        try:
            await self.memory_repo.upsert_from_log(
                user_id=user_id,
                food_name=log.food_name,
                calories=log.calories,
                portion_grams=log.portion_grams,
                protein_g=log.protein_g,
                carbs_g=log.carbs_g,
                fat_g=log.fat_g,
                raw_input=log.raw_input,
                embedding=embedding,
                is_correction=is_correction,
            )
        except Exception as e:
            logger.warning("memory_update_failed", error=str(e), food=log.food_name)
            # Never fail a log because memory update failed

    async def _refresh_daily_summary(
        self,
        user_id: UUID,
        target_date: date,
    ) -> None:
        totals = await self.food_repo.get_daily_nutrition_totals(user_id, target_date)
        await self.summary_repo.upsert_nutrition(
            user_id,
            target_date,
            total_calories_in=totals["total_calories"],
            total_protein_g=totals["total_protein"],
            total_carbs_g=totals["total_carbs"],
            total_fat_g=totals["total_fat"],
            total_fiber_g=totals["total_fiber"],
            food_log_count=totals["count"],
        )

    async def _record_correction(
        self,
        user_id: UUID,
        log_id: UUID,
        correction_type: str,
        original_value: float,
        corrected_value: float,
        original_source: str,
        original_confidence: float,
    ) -> None:
        from app.models.correction_event import CorrectionEvent
        event = CorrectionEvent(
            user_id=user_id,
            food_log_id=log_id,
            correction_type=correction_type,
            original_value=original_value,
            corrected_value=corrected_value,
            delta=corrected_value - original_value,
            original_estimation_source=original_source,
            original_confidence_score=original_confidence,
        )
        self.session.add(event)
        await self.session.flush()
        logger.info(
            "correction_recorded",
            type=correction_type,
            delta=event.delta,
            source=original_source,
        )
