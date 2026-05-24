"""
ProgressPhoto — a single image attached to a ProgressCheckpoint.

Storage design:
- `storage_key` is the opaque key passed to the StorageBackend
  (e.g., "{user_id}/2026/05/uuid.jpg" for local; S3 key for cloud)
- `storage_key` is NEVER exposed directly to clients — use get_url() to resolve
- Images are pre-processed (resized + compressed) before storage

A checkpoint can have multiple photos (front, back, side views).
`display_order` controls the rendering order in the UI.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.progress_checkpoint import ProgressCheckpoint
    from app.models.user import User


class ProgressPhoto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "progress_photos"
    __table_args__ = (
        Index("ix_progress_photos_checkpoint", "checkpoint_id", "display_order"),
        Index("ix_progress_photos_user", "user_id"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    checkpoint_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("progress_checkpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Storage ───────────────────────────────────────────────────────────────
    # Opaque storage key — resolved to URL via StorageBackend.get_url()
    # Never expose this to clients directly
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)

    # Original filename for display/download purposes only
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Content type after processing — always JPEG after compression
    content_type: Mapped[str] = mapped_column(
        String(50), default="image/jpeg", nullable=False
    )

    # ── Image Metadata ────────────────────────────────────────────────────────
    # Size of the PROCESSED image (post-compression), not the original
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width_px: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    height_px: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Display ───────────────────────────────────────────────────────────────
    # 0-indexed position within the checkpoint's photo set
    # 0 = primary/cover photo shown in list view
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Optional label: "front", "back", "side-left", "side-right"
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    checkpoint: Mapped[ProgressCheckpoint] = relationship(
        "ProgressCheckpoint", back_populates="photos", lazy="noload"
    )
    user: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<ProgressPhoto id={self.id} "
            f"checkpoint={self.checkpoint_id} order={self.display_order}>"
        )
