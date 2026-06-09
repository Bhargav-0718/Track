"""
WorkoutEstimationService — calorie estimation for cardio and strength.

Two-stage pipeline (mirrors food estimation):
  Stage 1: Cache lookup (string similarity on CardioActivityCache / ExerciseCache)
  Stage 2: LLM fallback → result saved to cache for future reuse

Strength scaling:
  When an exercise is cached, future logs with different weight/reps/sets
  scale proportionally via the stored calories_per_volume_unit.
"""
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from uuid import UUID

from app.core.logging import get_logger
from app.models.cardio_activity_cache import CardioActivityCache
from app.models.exercise_cache import ExerciseCache
from app.services.ai.llm_service import (
    CardioActivityEstimate,
    estimate_cardio_activity,
    estimate_strength_exercise,
)

logger = get_logger(__name__)

DEFAULT_WEIGHT_KG = 70.0
CACHE_SIMILARITY_THRESHOLD = 0.65


# ── Result dataclasses ─────────────────────────────────────────────────────────

@dataclass
class CardioResult:
    activity_description: str
    canonical_name: str
    duration_minutes: float
    calories_burned: float
    met_value: float
    calories_source: str   # "user_provided" | "cache" | "llm"
    assumptions: list[str] = field(default_factory=list)


@dataclass
class StrengthResult:
    exercise_name: str
    canonical_name: str
    sets: int
    reps: int
    weight_kg: float
    calories_burned: float
    calories_per_volume_unit: float
    calories_source: str   # "cache" | "llm"
    assumptions: list[str] = field(default_factory=list)


# ── Similarity helper ──────────────────────────────────────────────────────────

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _best_match(
    name: str,
    entries: list,
    threshold: float = CACHE_SIMILARITY_THRESHOLD,
) -> tuple | None:
    """Return (entry, score) for the best-matching cache entry, or None."""
    best_score = 0.0
    best_entry = None
    for entry in entries:
        names = [entry.activity_name if hasattr(entry, "activity_name") else entry.exercise_name]
        names += entry.aliases
        for n in names:
            score = _similarity(name, n)
            if score > best_score:
                best_score = score
                best_entry = entry
    if best_score >= threshold:
        return best_entry, best_score
    return None


# ── Service ────────────────────────────────────────────────────────────────────

class WorkoutEstimationService:

    # ── Cardio ─────────────────────────────────────────────────────────────────

    async def estimate_cardio(
        self,
        activity_description: str,
        duration_minutes: float,
        provided_calories: float | None,
        user_weight_kg: float,
    ) -> CardioResult:
        """Estimate calories for one cardio activity."""

        if provided_calories is not None:
            # User already knows — just try to cache the MET for future reuse
            met = provided_calories / (user_weight_kg * duration_minutes / 60) if duration_minutes > 0 else 5.0
            await self._upsert_cardio_cache(activity_description, met, source="user_provided")
            return CardioResult(
                activity_description=activity_description,
                canonical_name=activity_description,
                duration_minutes=duration_minutes,
                calories_burned=round(provided_calories, 1),
                met_value=round(met, 2),
                calories_source="user_provided",
                assumptions=["Calories provided by user"],
            )

        # Stage 1: Cache lookup
        all_cache = await CardioActivityCache.find_all().to_list()
        match = _best_match(activity_description, all_cache)

        if match:
            cached, score = match
            calories = round(cached.met_value * user_weight_kg * duration_minutes / 60, 1)
            logger.info("cardio_cache_hit", activity=activity_description, score=score, calories=calories)
            return CardioResult(
                activity_description=activity_description,
                canonical_name=cached.activity_name,
                duration_minutes=duration_minutes,
                calories_burned=calories,
                met_value=cached.met_value,
                calories_source="cache",
                assumptions=[
                    f"Matched '{cached.activity_name}' from cache (similarity {score:.0%})",
                    f"calories = {cached.met_value} MET × {user_weight_kg:.0f}kg × {duration_minutes:.0f}min/60",
                ],
            )

        # Stage 2: LLM fallback
        logger.info("cardio_llm_fallback", activity=activity_description)
        llm: CardioActivityEstimate = await estimate_cardio_activity(
            activity_description=activity_description,
            duration_minutes=duration_minutes,
            user_weight_kg=user_weight_kg,
        )
        await self._upsert_cardio_cache(llm.canonical_name, llm.met_value, source="llm", aliases=[activity_description])

        return CardioResult(
            activity_description=activity_description,
            canonical_name=llm.canonical_name,
            duration_minutes=duration_minutes,
            calories_burned=round(llm.estimated_calories, 1),
            met_value=llm.met_value,
            calories_source="llm",
            assumptions=llm.assumptions,
        )

    async def _upsert_cardio_cache(
        self,
        canonical_name: str,
        met_value: float,
        *,
        source: str,
        aliases: list[str] | None = None,
    ) -> None:
        existing = await CardioActivityCache.find_one(
            {"activity_name": {"$regex": canonical_name, "$options": "i"}}
        )
        if existing:
            return  # already cached
        entry = CardioActivityCache(
            activity_name=canonical_name,
            aliases=aliases or [],
            met_value=round(met_value, 2),
            source=source,
        )
        await entry.insert()
        logger.info("cardio_cache_saved", name=canonical_name, met=met_value)

    # ── Strength ───────────────────────────────────────────────────────────────

    async def estimate_strength(
        self,
        exercise_name: str,
        sets: int,
        reps: int,
        weight_kg: float,
        user_weight_kg: float,
    ) -> StrengthResult:
        """Estimate calories burned for one strength exercise set."""
        volume = sets * reps * weight_kg if weight_kg > 0 else sets * reps

        # Stage 1: Cache lookup
        all_cache = await ExerciseCache.find_all().to_list()
        match = _best_match(exercise_name, all_cache)

        if match:
            cached, score = match
            calories = round(cached.calories_per_volume_unit * volume, 1)
            logger.info("exercise_cache_hit", exercise=exercise_name, score=score, calories=calories)
            return StrengthResult(
                exercise_name=exercise_name,
                canonical_name=cached.exercise_name,
                sets=sets,
                reps=reps,
                weight_kg=weight_kg,
                calories_burned=calories,
                calories_per_volume_unit=cached.calories_per_volume_unit,
                calories_source="cache",
                assumptions=[
                    f"Matched '{cached.exercise_name}' from cache (similarity {score:.0%})",
                    f"Scaled cached rate {cached.calories_per_volume_unit:.4f} kcal/vol × volume {volume:.0f}",
                ],
            )

        # Stage 2: LLM fallback
        logger.info("exercise_llm_fallback", exercise=exercise_name)
        llm = await estimate_strength_exercise(
            exercise_name=exercise_name,
            sets=sets,
            reps=reps,
            weight_kg=weight_kg,
            user_weight_kg=user_weight_kg,
        )
        await self._upsert_exercise_cache(
            canonical_name=llm.canonical_name,
            calories_per_volume_unit=llm.calories_per_volume_unit,
            source="llm",
            aliases=[exercise_name],
            assumptions=llm.assumptions,
        )

        return StrengthResult(
            exercise_name=exercise_name,
            canonical_name=llm.canonical_name,
            sets=sets,
            reps=reps,
            weight_kg=weight_kg,
            calories_burned=round(llm.calories_burned, 1),
            calories_per_volume_unit=llm.calories_per_volume_unit,
            calories_source="llm",
            assumptions=llm.assumptions,
        )

    async def _upsert_exercise_cache(
        self,
        canonical_name: str,
        calories_per_volume_unit: float,
        *,
        source: str,
        aliases: list[str] | None = None,
        assumptions: list[str] | None = None,
    ) -> None:
        existing = await ExerciseCache.find_one(
            {"exercise_name": {"$regex": canonical_name, "$options": "i"}}
        )
        if existing:
            return
        entry = ExerciseCache(
            exercise_name=canonical_name,
            aliases=aliases or [],
            calories_per_volume_unit=round(calories_per_volume_unit, 6),
            source=source,
            llm_assumptions=assumptions or [],
        )
        await entry.insert()
        logger.info("exercise_cache_saved", name=canonical_name, rate=calories_per_volume_unit)
