"""
FoodMemory repository — vector similarity search + memory management.

Two search modes:
1. Exact text match (canonical_name or aliases) — fast, high confidence
2. Vector similarity (pgvector cosine distance) — semantic, handles variations

The HNSW index (Phase 2 migration) makes vector search fast:
- ~1ms for 10,000 vectors with ef_search=40
- Approximate nearest neighbor — occasionally misses the closest match
  by a tiny margin, which is acceptable for food similarity
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food_memory import FoodMemory
from app.repositories.base import BaseRepository


class FoodMemoryRepository(BaseRepository[FoodMemory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FoodMemory, session)

    async def get_by_canonical_name(
        self,
        user_id: UUID,
        canonical_name: str,
    ) -> FoodMemory | None:
        """Exact match on canonical name (case-insensitive)."""
        result = await self.session.execute(
            select(FoodMemory).where(
                FoodMemory.user_id == user_id,
                func.lower(FoodMemory.canonical_name) == canonical_name.lower().strip(),
            )
        )
        return result.scalar_one_or_none()

    async def vector_similarity_search(
        self,
        user_id: UUID,
        query_embedding: list[float],
        *,
        limit: int = 3,
        max_distance: float = 0.4,   # Cosine distance threshold (0=identical, 2=opposite)
    ) -> list[tuple[FoodMemory, float]]:
        """
        Find semantically similar foods using pgvector cosine distance.

        Distance thresholds for Indian food context:
        - < 0.1: Very likely the same dish (different spellings)
        - 0.1-0.2: Very similar dishes (dal makhani vs dal tadka)
        - 0.2-0.35: Related dishes (butter chicken vs chicken curry)
        - > 0.4: Different enough to not be reliable

        Returns list of (FoodMemory, similarity_score) where score is 1 - distance.
        """
        try:
            from pgvector.sqlalchemy import Vector
        except ImportError:
            return []   # pgvector not available — graceful degradation

        distance_expr = FoodMemory.embedding.cosine_distance(query_embedding)

        result = await self.session.execute(
            select(FoodMemory, distance_expr.label("distance"))
            .where(
                and_(
                    FoodMemory.user_id == user_id,
                    FoodMemory.embedding.is_not(None),
                    distance_expr <= max_distance,
                )
            )
            .order_by(distance_expr)
            .limit(limit)
        )

        rows = result.all()
        # Convert distance to similarity score (1 - distance, capped at 1.0)
        return [(row[0], round(1.0 - float(row[1]), 3)) for row in rows]

    async def get_recent_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
    ) -> list[FoodMemory]:
        """Get user's most recently logged foods from memory."""
        result = await self.session.execute(
            select(FoodMemory)
            .where(FoodMemory.user_id == user_id)
            .order_by(FoodMemory.last_logged_at.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_frequent_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
    ) -> list[FoodMemory]:
        """Get user's most frequently logged foods."""
        result = await self.session.execute(
            select(FoodMemory)
            .where(FoodMemory.user_id == user_id)
            .order_by(FoodMemory.log_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

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
          Corrections are weighted 3× higher — they carry ground truth signal.

        Confidence score formula:
          base = min(log_count / 10, 0.85)           # Grows with experience
          penalty = correction_rate × 0.15            # Penalizes systematic errors
          final = max(base - penalty, 0.2)            # Floor at 0.2
        """
        existing = await self.get_by_canonical_name(user_id, food_name)

        if existing is None:
            # First time logging this food
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
                last_logged_at=datetime.now(timezone.utc),
                confidence_score=0.3,  # Low confidence on first entry
                metadata_={},
            )
            if embedding:
                try:
                    memory.embedding = embedding
                except AttributeError:
                    pass  # pgvector not available
            self.session.add(memory)
            await self.session.flush()
            await self.session.refresh(memory)
            return memory

        # Update existing memory
        n = existing.log_count

        if is_correction:
            # Correction: 70% weight on new value (ground truth signal)
            weight_old, weight_new = 0.3, 0.7
            existing.correction_count += 1
        else:
            # Normal log: incremental weighted average
            weight_old = n / (n + 1)
            weight_new = 1 / (n + 1)

        # Update averages
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

        # Add alias if new raw_input is different
        if raw_input and raw_input.lower() not in [a.lower() for a in (existing.aliases or [])]:
            aliases = list(existing.aliases or [])
            if raw_input.lower() != food_name.lower():
                aliases.append(raw_input)
            existing.aliases = aliases[:20]  # Cap at 20 aliases

        existing.log_count = n + 1
        existing.last_logged_at = datetime.now(timezone.utc)

        # Update confidence score
        correction_rate = existing.correction_count / existing.log_count
        base = min(existing.log_count / 10, 0.85)
        penalty = correction_rate * 0.15
        existing.confidence_score = round(max(base - penalty, 0.2), 3)

        # Update embedding if provided
        if embedding:
            try:
                existing.embedding = embedding
            except AttributeError:
                pass

        await self.session.flush()
        await self.session.refresh(existing)
        return existing
