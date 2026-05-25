"""
ProgressCheckpoint — a dated physique snapshot with optional photos.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from app.models.base import BaseDocument


class ProgressCheckpoint(BaseDocument):
    # ── References ────────────────────────────────────────────────────────────
    user_id: UUID

    # ── Checkpoint Date ────────────────────────────────────────────────────────
    checkpoint_date: date

    # ── Body Metrics ──────────────────────────────────────────────────────────
    weight_kg: float | None = None
    body_fat_percentage: float | None = None

    # ── Qualitative Context ───────────────────────────────────────────────────
    notes: str | None = None
    tags: list[str] = []

    # ── Soft Delete ───────────────────────────────────────────────────────────
    is_deleted: bool = False

    class Settings:
        name = "progress_checkpoints"

    def __repr__(self) -> str:
        return (
            f"<ProgressCheckpoint id={self.id} "
            f"date={self.checkpoint_date} weight={self.weight_kg}kg>"
        )
