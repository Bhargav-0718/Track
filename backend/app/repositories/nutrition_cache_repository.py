"""
NutritionCache repository — fuzzy text search using Python difflib.

Replaces pg_trgm similarity search with Python SequenceMatcher.
Works for bounded nutrition datasets (1000-5000 entries).
"""
from difflib import SequenceMatcher
from uuid import UUID

from app.models.nutrition_cache import NutritionCache
from app.repositories.base import BaseRepository


def _trgm_similarity(a: str, b: str) -> float:
    """
    Approximate trigram similarity using SequenceMatcher.
    Returns 0.0–1.0, same scale as PostgreSQL pg_trgm similarity().
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class NutritionCacheRepository(BaseRepository[NutritionCache]):
    def __init__(self) -> None:
        super().__init__(NutritionCache)

    async def fuzzy_search(
        self,
        query: str,
        *,
        limit: int = 5,
        min_similarity: float = 0.15,
    ) -> list[tuple[NutritionCache, float]]:
        """
        Search nutrition cache using Python string similarity.

        Fetches all entries and scores them in Python.
        Efficient for typical nutrition cache sizes (< 10,000 entries).
        """
        all_entries = await NutritionCache.find_all().to_list()
        results: list[tuple[NutritionCache, float]] = []

        for entry in all_entries:
            score = _trgm_similarity(entry.food_name, query)
            if score >= min_similarity:
                results.append((entry, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def search_with_aliases(
        self,
        primary_name: str,
        aliases: list[str],
        *,
        limit: int = 3,
    ) -> list[tuple[NutritionCache, float]]:
        """
        Search for a food using primary name and aliases.
        Deduplicates results and returns best match per food.
        """
        all_names = [primary_name] + aliases[:5]
        seen_ids: set[UUID] = set()
        results: list[tuple[NutritionCache, float]] = []

        for name in all_names:
            if not name.strip():
                continue
            matches = await self.fuzzy_search(name, limit=limit, min_similarity=0.15)
            for food, score in matches:
                if food.id not in seen_ids:
                    seen_ids.add(food.id)
                    results.append((food, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def get_by_external_id(
        self,
        source: str,
        external_id: str,
    ) -> NutritionCache | None:
        """Get a cache entry by source + external ID."""
        return await NutritionCache.find_one(
            NutritionCache.source == source,
            NutritionCache.external_id == external_id,
        )

    async def bulk_insert_ignore_conflicts(
        self,
        entries: list[NutritionCache],
    ) -> int:
        """Insert multiple cache entries, skipping duplicates."""
        inserted = 0
        for entry in entries:
            existing = await self.get_by_external_id(entry.source, entry.external_id or "")
            if not existing:
                await entry.insert()
                inserted += 1
        return inserted
