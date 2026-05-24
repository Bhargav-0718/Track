"""
NutritionCache repository — fuzzy text search using pg_trgm.

The pg_trgm extension (enabled in init_db.sql) allows similarity-based
text search without exact matching. This handles:
- Spelling variations: "paneer" vs "Paneer"
- Partial matches: "dal" finds "Dal Makhani", "Moong Dal", "Dal Tadka"
- Alias searching: try multiple names for the same dish

The GIN trgm index (added in Phase 2 migration) makes this fast even
at 1000+ food entries.
"""
from uuid import UUID

from sqlalchemy import Float, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nutrition_cache import NutritionCache
from app.repositories.base import BaseRepository


class NutritionCacheRepository(BaseRepository[NutritionCache]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NutritionCache, session)

    async def fuzzy_search(
        self,
        query: str,
        *,
        limit: int = 5,
        min_similarity: float = 0.15,
    ) -> list[tuple[NutritionCache, float]]:
        """
        Search nutrition cache using pg_trgm similarity.

        Returns list of (NutritionCache, similarity_score) tuples,
        ordered by similarity descending.

        min_similarity=0.15 is intentionally low to catch partial matches
        like "dal" → "Dal Makhani". The caller decides what score is "good enough".
        """
        similarity_expr = func.similarity(NutritionCache.food_name, query)

        result = await self.session.execute(
            select(NutritionCache, similarity_expr.label("sim"))
            .where(similarity_expr >= min_similarity)
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        rows = result.all()
        return [(row[0], float(row[1])) for row in rows]

    async def search_with_aliases(
        self,
        primary_name: str,
        aliases: list[str],
        *,
        limit: int = 3,
    ) -> list[tuple[NutritionCache, float]]:
        """
        Search for a food using its primary name and multiple aliases.

        Strategy:
        1. Run similarity search for each name
        2. Deduplicate results by food ID
        3. Return best match per food, ordered by highest similarity

        This handles cases where:
        - "murgh makhani" alias finds "Butter Chicken" in DB
        - "dal" finds "Dal Makhani", "Moong Dal", "Chana Dal"
        """
        all_names = [primary_name] + aliases[:5]   # Cap at 6 total searches
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

        # Sort by score descending and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def get_by_external_id(
        self,
        source: str,
        external_id: str,
    ) -> NutritionCache | None:
        """Get a cache entry by source + external ID (for deduplication during import)."""
        result = await self.session.execute(
            select(NutritionCache).where(
                NutritionCache.source == source,
                NutritionCache.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def bulk_insert_ignore_conflicts(
        self,
        entries: list[NutritionCache],
    ) -> int:
        """
        Insert multiple cache entries, skipping duplicates.
        Returns number of actually inserted records.
        Used during dataset import.
        """
        inserted = 0
        for entry in entries:
            existing = await self.get_by_external_id(entry.source, entry.external_id or "")
            if not existing:
                self.session.add(entry)
                inserted += 1

        await self.session.flush()
        return inserted
