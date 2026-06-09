"""
CardioActivityCache — stores MET values for cardio activities.

Similar role to NutritionCache for food: seed from LLM once,
reuse forever. MET (Metabolic Equivalent of Task) lets us compute
calories = MET × weight_kg × (duration_minutes / 60) for any user.
"""
from app.models.base import BaseDocument


class CardioActivityCache(BaseDocument):
    activity_name: str          # canonical English name, e.g. "Treadmill Walk"
    aliases: list[str] = []     # spelling variants for fuzzy lookup
    met_value: float            # MET for this activity
    source: str = "llm"         # "llm" | "formula"
    description: str | None = None  # optional modifier captured from input

    class Settings:
        name = "cardio_activity_cache"

    def __repr__(self) -> str:
        return f"<CardioActivityCache name='{self.activity_name}' MET={self.met_value}>"
