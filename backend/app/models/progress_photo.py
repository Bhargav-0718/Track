"""
ProgressPhoto — a single image attached to a ProgressCheckpoint.
"""
from __future__ import annotations

from uuid import UUID

from app.models.base import BaseDocument


class ProgressPhoto(BaseDocument):
    # ── References ────────────────────────────────────────────────────────────
    checkpoint_id: UUID
    user_id: UUID

    # ── Storage ───────────────────────────────────────────────────────────────
    storage_key: str
    original_filename: str | None = None
    content_type: str = "image/jpeg"

    # ── Image Metadata ────────────────────────────────────────────────────────
    file_size_bytes: int = 0
    width_px: int = 0
    height_px: int = 0

    # ── Display ───────────────────────────────────────────────────────────────
    display_order: int = 0
    label: str | None = None

    class Settings:
        name = "progress_photos"

    def __repr__(self) -> str:
        return (
            f"<ProgressPhoto id={self.id} "
            f"checkpoint={self.checkpoint_id} order={self.display_order}>"
        )
