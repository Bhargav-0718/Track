"""
FoodMemory — the semantic memory store for personalized food recognition.

Every time a user logs the same food, this record gets smarter.
Embeddings enable semantic similarity search (Python cosine similarity).
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from beanie import Indexed
from pymongo import ASCENDING

from app.models.base import BaseDocument


class FoodMemory(BaseDocument):
    # ── References ────────────────────────────────────────────────────────────
    user_id: UUID

    # ── Food Identity ─────────────────────────────────────────────────────────
    canonical_name: str
    aliases: list[str] = []

    # ── Learned Nutrition (Weighted Averages) ─────────────────────────────────
    avg_calories: float
    avg_portion_grams: float | None = None
    avg_protein_g: float | None = None
    avg_carbs_g: float | None = None
    avg_fat_g: float | None = None

    # ── Learning Signals ──────────────────────────────────────────────────────
    log_count: int = 1
    correction_count: int = 0
    last_logged_at: datetime | None = None

    # ── Confidence ────────────────────────────────────────────────────────────
    confidence_score: float = 0.5

    # ── Semantic Embedding ────────────────────────────────────────────────────
    # 1536-dim vector; cosine similarity computed in Python
    embedding: list[float] | None = None

    # ── Flexible Metadata ─────────────────────────────────────────────────────
    metadata_: dict = {}

    class Settings:
        name = "food_memory"
        indexes = [
            # Unique: one memory per food per user
            [("user_id", ASCENDING), ("canonical_name", ASCENDING)],
        ]

    def __repr__(self) -> str:
        return (
            f"<FoodMemory id={self.id} food='{self.canonical_name}' "
            f"logs={self.log_count} confidence={self.confidence_score:.2f}>"
        )
