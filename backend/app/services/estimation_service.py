"""
EstimationService — the full calorie estimation pipeline.

This is the core intelligence of the platform. It orchestrates:

  Stage 1: MEMORY    → pgvector similarity search on user's food history
  Stage 2: DATABASE  → pg_trgm fuzzy search on INDB Indian food dataset
  Stage 3: LLM       → GPT-4o mini fallback with structured output

Each stage has a confidence threshold. The pipeline short-circuits as soon
as it finds a result above the threshold for that stage.

Returns an EstimationResult which the FoodService uses to create a food log.

IMPORTANT: The LLM is never the first choice. It is the last resort.
When the LLM is used, the result is clearly marked as 'uncertain' in the UI.
"""
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CalorieEstimationError
from app.core.logging import get_logger
from app.core.portions import estimate_grams_from_description
from app.models.food_memory import FoodMemory
from app.models.nutrition_cache import NutritionCache
from app.repositories.food_memory_repository import FoodMemoryRepository
from app.repositories.nutrition_cache_repository import NutritionCacheRepository
from app.schemas.common import ConfidenceLevel, EstimationSource
from app.services.ai.embedding_service import embed_text
from app.services.ai.llm_service import FoodParseResult, estimate_nutrition_fallback, parse_food_input

logger = get_logger(__name__)


# ── Result Type ────────────────────────────────────────────────────────────────

@dataclass
class EstimationResult:
    """Complete result from the estimation pipeline."""
    # Food identity
    food_name: str
    portion_description: str
    portion_grams: float

    # Nutrition (always calories, macros optional)
    calories: float
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None

    # Provenance
    estimation_source: str = EstimationSource.MANUAL
    confidence_score: float = 1.0
    confidence_level: str = ConfidenceLevel.CONFIRMED
    assumptions: list[str] = field(default_factory=list)

    # References for storage (link back to source records)
    memory_id: UUID | None = None
    nutrition_cache_id: UUID | None = None

    # Parsed data for memory update
    parse_result: FoodParseResult | None = None


# ── Confidence Thresholds ──────────────────────────────────────────────────────

MEMORY_HIGH_CONFIDENCE = 0.85      # Similarity score to accept memory hit directly
MEMORY_LOW_CONFIDENCE = 0.60       # Minimum similarity to attempt memory + DB blend
DB_HIGH_CONFIDENCE = 0.45          # Trgm similarity score for "good" DB match
DB_LOW_CONFIDENCE = 0.20           # Minimum similarity to use DB with lower confidence


class EstimationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.memory_repo = FoodMemoryRepository(session)
        self.nutrition_repo = NutritionCacheRepository(session)

    async def estimate(
        self,
        raw_input: str,
        user_id: UUID,
    ) -> EstimationResult:
        """
        Run the full 3-stage estimation pipeline for a food log entry.

        Args:
            raw_input: The user's natural language food description
            user_id: The authenticated user's ID (memory is user-scoped)

        Returns:
            EstimationResult with nutrition, confidence, and provenance
        """
        # ── Step 1: Parse the input with LLM ──────────────────────────────────
        # Always runs — cheap, fast, necessary for all subsequent steps
        parse_result = await parse_food_input(raw_input)

        logger.info(
            "estimation_started",
            raw_input=raw_input[:80],
            parsed_food=parse_result.food_name,
            estimated_grams=parse_result.estimated_grams,
        )

        # Resolve portion grams — try local lookup table first (no LLM cost)
        portion_match = estimate_grams_from_description(parse_result.portion_description)
        if portion_match:
            portion_grams = portion_match.estimated_grams
            logger.debug("portion_resolved_locally", grams=portion_grams, desc=portion_match.description)
        else:
            portion_grams = parse_result.estimated_grams

        # ── Step 2: Memory Lookup ──────────────────────────────────────────────
        memory_result = await self._search_memory(
            user_id=user_id,
            parse_result=parse_result,
        )

        if memory_result:
            memory, sim_score = memory_result
            if sim_score >= MEMORY_HIGH_CONFIDENCE:
                return self._result_from_memory(
                    memory=memory,
                    portion_grams=portion_grams,
                    parse_result=parse_result,
                    similarity=sim_score,
                )
            # Low-confidence memory hit: continue to DB, use memory as context

        # ── Step 3: Database Lookup ────────────────────────────────────────────
        db_result = await self._search_database(parse_result=parse_result)

        if db_result:
            cache_entry, trgm_score = db_result
            if trgm_score >= DB_LOW_CONFIDENCE:
                return self._result_from_database(
                    cache_entry=cache_entry,
                    portion_grams=portion_grams,
                    parse_result=parse_result,
                    trgm_score=trgm_score,
                )

        # ── Step 4: LLM Fallback ──────────────────────────────────────────────
        # Only reached if BOTH memory and database failed
        logger.info(
            "estimation_llm_fallback",
            food_name=parse_result.food_name,
            reason="no memory or DB match",
        )

        # Build context from partial DB match if any
        context = None
        if db_result:
            cache_entry, score = db_result
            context = (
                f"Closest database match: '{cache_entry.food_name}' = "
                f"{cache_entry.calories_per_100g:.0f} kcal/100g "
                f"(similarity {score:.2f} — not confident enough to use directly)"
            )

        llm_estimate = await estimate_nutrition_fallback(
            food_name=parse_result.food_name,
            context=context,
        )

        total_calories = (llm_estimate.calories_per_100g * portion_grams) / 100
        total_protein = (llm_estimate.protein_per_100g * portion_grams / 100) if llm_estimate.protein_per_100g else None
        total_carbs = (llm_estimate.carbs_per_100g * portion_grams / 100) if llm_estimate.carbs_per_100g else None
        total_fat = (llm_estimate.fat_per_100g * portion_grams / 100) if llm_estimate.fat_per_100g else None

        assumptions = list(llm_estimate.assumptions)
        assumptions.append(f"Portion estimated at {portion_grams:.0f}g ({parse_result.portion_description})")

        logger.info(
            "estimation_llm_complete",
            food=parse_result.food_name,
            calories=round(total_calories),
            confidence=llm_estimate.confidence_score,
        )

        return EstimationResult(
            food_name=parse_result.food_name,
            portion_description=parse_result.portion_description,
            portion_grams=portion_grams,
            calories=round(total_calories, 1),
            protein_g=round(total_protein, 1) if total_protein else None,
            carbs_g=round(total_carbs, 1) if total_carbs else None,
            fat_g=round(total_fat, 1) if total_fat else None,
            estimation_source=EstimationSource.LLM,
            confidence_score=llm_estimate.confidence_score,
            confidence_level=ConfidenceLevel.UNCERTAIN,
            assumptions=assumptions,
            parse_result=parse_result,
        )

    # ── Internal Stage Methods ─────────────────────────────────────────────────

    async def _search_memory(
        self,
        user_id: UUID,
        parse_result: FoodParseResult,
    ) -> tuple[FoodMemory, float] | None:
        """
        Stage 1: Search user's food memory using both exact text and vector similarity.
        Returns best match (memory, similarity_score) or None.
        """
        # Try exact text match first (fast, free)
        exact = await self.memory_repo.get_by_canonical_name(
            user_id, parse_result.food_name
        )
        if exact:
            logger.info("memory_exact_hit", food=parse_result.food_name, confidence=exact.confidence_score)
            return exact, min(0.95, 0.7 + exact.confidence_score * 0.3)  # Scale to similarity

        # Try vector similarity search
        try:
            embedding = await embed_text(parse_result.food_name)
            vector_results = await self.memory_repo.vector_similarity_search(
                user_id=user_id,
                query_embedding=embedding,
                limit=3,
                max_distance=0.35,
            )
            if vector_results:
                best_memory, sim = vector_results[0]
                logger.info(
                    "memory_vector_hit",
                    query=parse_result.food_name,
                    matched=best_memory.canonical_name,
                    similarity=sim,
                )
                return best_memory, sim
        except Exception as e:
            logger.warning("memory_vector_search_failed", error=str(e))

        return None

    async def _search_database(
        self,
        parse_result: FoodParseResult,
    ) -> tuple[NutritionCache, float] | None:
        """
        Stage 2: Search the INDB nutrition cache using pg_trgm fuzzy text matching.
        Returns best match (cache_entry, similarity_score) or None.
        """
        results = await self.nutrition_repo.search_with_aliases(
            primary_name=parse_result.food_name,
            aliases=parse_result.aliases,
            limit=5,
        )

        if not results:
            return None

        best_entry, best_score = results[0]
        logger.info(
            "db_search_result",
            query=parse_result.food_name,
            matched=best_entry.food_name,
            score=best_score,
            source=best_entry.source,
        )
        return best_entry, best_score

    # ── Result Builders ────────────────────────────────────────────────────────

    def _result_from_memory(
        self,
        memory: FoodMemory,
        portion_grams: float,
        parse_result: FoodParseResult,
        similarity: float,
    ) -> EstimationResult:
        """Build result from a food_memory hit."""
        # Memory stores avg_calories as per 100g
        scale = portion_grams / 100.0
        calories = memory.avg_calories * scale
        protein = (memory.avg_protein_g * scale) if memory.avg_protein_g else None
        carbs = (memory.avg_carbs_g * scale) if memory.avg_carbs_g else None
        fat = (memory.avg_fat_g * scale) if memory.avg_fat_g else None

        confidence_score = round(min(similarity * memory.confidence_score + 0.1, 1.0), 2)
        confidence_level = (
            ConfidenceLevel.CONFIRMED if confidence_score >= 0.85
            else ConfidenceLevel.ESTIMATED
        )

        assumptions = [
            f"Retrieved from your food history ({memory.log_count} previous logs)",
            f"Portion: {parse_result.portion_description} ≈ {portion_grams:.0f}g",
        ]
        if similarity < 0.9:
            assumptions.append(
                f"Matched '{memory.canonical_name}' (similarity: {similarity:.0%})"
            )

        return EstimationResult(
            food_name=memory.canonical_name,
            portion_description=parse_result.portion_description,
            portion_grams=portion_grams,
            calories=round(calories, 1),
            protein_g=round(protein, 1) if protein else None,
            carbs_g=round(carbs, 1) if carbs else None,
            fat_g=round(fat, 1) if fat else None,
            estimation_source=EstimationSource.MEMORY,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            assumptions=assumptions,
            memory_id=memory.id,
            parse_result=parse_result,
        )

    def _result_from_database(
        self,
        cache_entry: NutritionCache,
        portion_grams: float,
        parse_result: FoodParseResult,
        trgm_score: float,
    ) -> EstimationResult:
        """Build result from a nutrition_cache DB hit."""
        scale = portion_grams / 100.0
        calories = cache_entry.calories_per_100g * scale
        protein = (cache_entry.protein_per_100g * scale) if cache_entry.protein_per_100g else None
        carbs = (cache_entry.carbs_per_100g * scale) if cache_entry.carbs_per_100g else None
        fat = (cache_entry.fat_per_100g * scale) if cache_entry.fat_per_100g else None
        fiber = (cache_entry.fiber_per_100g * scale) if cache_entry.fiber_per_100g else None

        # Scale confidence: trgm_score 0.15→0.45 maps to confidence 0.45→0.75
        confidence_score = round(min(0.45 + trgm_score * 0.75, 0.82), 2)
        confidence_level = (
            ConfidenceLevel.ESTIMATED if trgm_score >= DB_HIGH_CONFIDENCE
            else ConfidenceLevel.UNCERTAIN
        )

        assumptions = [
            f"Data source: INDB Indian Food Composition Database",
            f"Matched '{cache_entry.food_name}' (similarity: {trgm_score:.0%})",
            f"Portion: {parse_result.portion_description} ≈ {portion_grams:.0f}g",
        ]
        if parse_result.food_name.lower() != cache_entry.food_name.lower():
            assumptions.append(
                f"Your input '{parse_result.food_name}' matched database entry '{cache_entry.food_name}'"
            )

        return EstimationResult(
            food_name=cache_entry.food_name,
            portion_description=parse_result.portion_description,
            portion_grams=portion_grams,
            calories=round(calories, 1),
            protein_g=round(protein, 1) if protein else None,
            carbs_g=round(carbs, 1) if carbs else None,
            fat_g=round(fat, 1) if fat else None,
            fiber_g=round(fiber, 1) if fiber else None,
            estimation_source=EstimationSource.DATASET,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            assumptions=assumptions,
            nutrition_cache_id=cache_entry.id,
            parse_result=parse_result,
        )
