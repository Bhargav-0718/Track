"""Phase 2: Add fuzzy search and vector similarity indexes

Revision ID: phase2_search_indexes
Revises:
Create Date: 2026-05-24 00:00:00

Changes:
- GIN trgm index on nutrition_cache.food_name (enables fuzzy food search)
- GIN trgm index on food_memory.canonical_name (enables fuzzy memory search)
- HNSW vector index on food_memory.embedding (enables fast similarity search)
- HNSW vector index on food_logs.embedding (for Phase 3 photo matching)

Why HNSW over IVFFlat?
- HNSW: No training phase needed, better recall at small dataset sizes (<100k vectors)
- IVFFlat: Better for very large datasets (>1M vectors) — not our use case
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "phase2_search_indexes"
down_revision: Union[str, None] = "phase1_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions already enabled in phase1_initial_schema (idempotent anyway)

    # ── GIN trgm index on nutrition_cache.food_name ────────────────────────────
    # Enables: WHERE similarity(food_name, 'butter chicken') > 0.15
    # Without this index: full table scan on every food lookup
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_nutrition_cache_food_name_trgm
        ON nutrition_cache
        USING GIN (food_name gin_trgm_ops)
    """)

    # ── GIN trgm index on food_memory.canonical_name ───────────────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_memory_canonical_name_trgm
        ON food_memory
        USING GIN (canonical_name gin_trgm_ops)
    """)

    # ── HNSW vector index on food_memory.embedding ─────────────────────────────
    # Parameters:
    # - m=16: Max connections per node (higher = better recall, more memory)
    # - ef_construction=64: Build-time search width (higher = better graph, slower build)
    # At 1000 food memories (personal use): build takes <1s, search takes <1ms
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_memory_embedding_hnsw
        ON food_memory
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # ── HNSW vector index on food_logs.embedding (Phase 3 prep) ───────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_logs_embedding_hnsw
        ON food_logs
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # ── Additional source index on nutrition_cache ─────────────────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_nutrition_cache_source
        ON nutrition_cache (source)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_nutrition_cache_food_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_food_memory_canonical_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_food_memory_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_food_logs_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_nutrition_cache_source")
