"""
FoodMemory repository — Python cosine similarity search + memory management.

Two search modes:
1. Exact text match (canonical_name) — fast, high confidence
2. Python cosine similarity on embeddings — semantic, handles variations

For Atlas deployments, can upgrade to Atlas Vector Search for O(log n) ANN.
"""
import math
from datetime import datetime
from datetime import timezone as dt_timezone
from uuid import UUID

from app.models.food_memory import FoodMemory
from app.repositories.base import BaseRepository


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class FoodMemoryRepository(BaseRepository[FoodMemory]):
    def __init__(self) -> None:
        super().__init__(FoodMemory)

    async def get_by_canonical_name(
        self,
        user_id: UUID,
        canonical_name: str,
    ) -> FoodMemory | None:
        """Exact match on canonical name (case-insensitive)."""
        # Fetch all user memories then filter in Python for case-insensitivity
        all_memories = await FoodMemory.find(FoodMemory.user_id == user_id).to_list()
        name_lower = canonical_name.lower().strip()
        for memory in all_memories:
            if memory.canonical_name.lower() == name_lower:
                return memory
        return None

    async def vector_similarity_search(
        self,
        user_id: UUID,
        query_embedding: list[float],
        *,
        limit: int = 3,
        max_distance: float = 0.4,
    ) -> list[tuple[FoodMemory, float]]:
        """
        Find semantically similar foods using Python cosine similarity.

        max_distance is cosine DISTANCE (0=identical, 2=opposite).
        Similarity = 1 - distance, so max_distance=0.4 → min_similarity=0.6.

        For Atlas Vector Search upgrade, replace this with:
            db["food_memory"].aggregate([{$vectorSearch: {...}}])
        """
        min_similarity = 1.0 - max_distance

        memories = await FoodMemory.find(
            FoodMemory.user_id == user_id,
        ).to_list()

        results: list[tuple[FoodMemory, float]] = []
        for memory in memories:
            if not memory.embedding:
                continue
            sim = _cosine_similarity(query_embedding, memory.embedding)
            if sim >= min_similarity:
                results.append((memory, round(sim, 3)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def get_recent_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
    ) -> list[FoodMemory]:
        """Get user's most recently logged foods."""
        memories = await FoodMemory.find(
            FoodMemory.user_id == user_id,
        ).sort(-FoodMemory.last_logged_at).limit(limit).to_list()
        return memories

    async def get_frequent_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
    ) -> list[FoodMemory]:
        """Get user's most frequently logged foods."""
        return await FoodMemory.find(
            FoodMemory.user_id == user_id,
        ).sort(-FoodMemory.log_count).limit(limit).to_list()

    async def upsert_from_log(
        self,
        user_id: UUID,
        food_name: str,
        calories: float,
        *,
        portion_grams: float | None = None,
        protein_g: float | None = None,
        carbs_g: float | None = None,
        fat_g: float | None = None,
        raw_input: str | None = None,
        embedding: list[float] | None = None,
        is_correction: bool = False,
    ) -> FoodMemory:
        """
        Create or update a food memory entry after a food log is saved.

        Update strategy (weighted moving average):
        - Normal log: new_avg = (old_avg × count + new_value) / (count + 1)
        - Correction: new_avg = (old_avg × 0.3 + corrected_value × 0.7)
        """
        existing = await self.get_by_canonical_name(user_id, food_name)

        if existing is None:
            memory = FoodMemory(
                user_id=user_id,
                canonical_name=food_name,
                aliases=[raw_input] if raw_input and raw_input.lower() != food_name.lower() else [],
                avg_calories=calories,
                avg_portion_grams=portion_grams,
                avg_protein_g=protein_g,
                avg_carbs_g=carbs_g,
                avg_fat_g=fat_g,
                log_count=1,
                correction_count=1 if is_correction else 0,
                last_logged_at=datetime.now(dt_timezone.utc),
                confidence_score=0.3,
                embedding=embedding,
                metadata_={},
            )
            await memory.insert()
            return memory

        n = existing.log_count

        if is_correction:
            weight_old, weight_new = 0.3, 0.7
            existing.correction_count += 1
        else:
            weight_old = n / (n + 1)
            weight_new = 1 / (n + 1)

        existing.avg_calories = existing.avg_calories * weight_old + calories * weight_new

        if portion_grams is not None:
            old_portion = existing.avg_portion_grams or portion_grams
            existing.avg_portion_grams = old_portion * weight_old + portion_grams * weight_new

        if protein_g is not None:
            old_p = existing.avg_protein_g or protein_g
            existing.avg_protein_g = old_p * weight_old + protein_g * weight_new

        if carbs_g is not None:
            old_c = existing.avg_carbs_g or carbs_g
            existing.avg_carbs_g = old_c * weight_old + carbs_g * weight_new

        if fat_g is not None:
            old_f = existing.avg_fat_g or fat_g
            existing.avg_fat_g = old_f * weight_old + fat_g * weight_new

        if raw_input and raw_input.lower() not in [a.lower() for a in (existing.aliases or [])]:
            aliases = list(existing.aliases or [])
            if raw_input.lower() != food_name.lower():
                aliases.append(raw_input)
            existing.aliases = aliases[:20]

        existing.log_count = n + 1
        existing.last_logged_at = datetime.now(dt_timezone.utc)

        correction_rate = existing.correction_count / existing.log_count
        base = min(existing.log_count / 10, 0.85)
        penalty = correction_rate * 0.15
        existing.confidence_score = round(max(base - penalty, 0.2), 3)

        if embedding:
            existing.embedding = embedding

        existing.updated_at = datetime.now(dt_timezone.utc)
        await existing.save()
        return existing
