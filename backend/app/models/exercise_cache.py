"""
ExerciseCache — stores calorie rate for strength exercises.

Caches LLM estimates so we avoid repeated LLM calls for the same
exercise. The rate is stored per unit of "volume" (sets × reps × weight_kg)
so future logs with different loads can be scaled proportionally:

    estimated_calories = cached_rate × new_volume
"""
from app.models.base import BaseDocument


class ExerciseCache(BaseDocument):
    exercise_name: str           # canonical name, e.g. "Bench Press"
    aliases: list[str] = []      # variants for fuzzy lookup
    calories_per_volume_unit: float  # kcal per (sets × reps × weight_kg)
    source: str = "llm"
    llm_assumptions: list[str] = []

    class Settings:
        name = "exercise_cache"

    def __repr__(self) -> str:
        return (
            f"<ExerciseCache name='{self.exercise_name}' "
            f"rate={self.calories_per_volume_unit:.4f} kcal/vol>"
        )
