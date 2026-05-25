"""
CheckpointRepository — data access for progress checkpoints and photos.
"""
from datetime import date, datetime
from datetime import timezone as dt_timezone
from uuid import UUID

from app.models.progress_checkpoint import ProgressCheckpoint
from app.models.progress_photo import ProgressPhoto


class CheckpointRepository:
    # ── Checkpoints ────────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: UUID,
        checkpoint_date: date,
        weight_kg: float | None = None,
        body_fat_percentage: float | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> ProgressCheckpoint:
        checkpoint = ProgressCheckpoint(
            user_id=user_id,
            checkpoint_date=checkpoint_date,
            weight_kg=weight_kg,
            body_fat_percentage=body_fat_percentage,
            notes=notes,
            tags=tags or [],
        )
        await checkpoint.insert()
        return checkpoint

    async def get_by_id_for_user(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
        load_photos: bool = True,
    ) -> ProgressCheckpoint | None:
        """Fetch a checkpoint (photos loaded separately if needed)."""
        return await ProgressCheckpoint.find_one(
            ProgressCheckpoint.id == checkpoint_id,
            ProgressCheckpoint.user_id == user_id,
            ProgressCheckpoint.is_deleted == False,  # noqa: E712
        )

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        date_from: date | None = None,
        date_to: date | None = None,
        tags: list[str] | None = None,
    ) -> tuple[list[ProgressCheckpoint], int]:
        """Paginated list of checkpoints, newest first."""
        all_checkpoints = await ProgressCheckpoint.find(
            ProgressCheckpoint.user_id == user_id,
            ProgressCheckpoint.is_deleted == False,  # noqa: E712
        ).to_list()

        # Apply Python-side date filters
        if date_from:
            all_checkpoints = [c for c in all_checkpoints if c.checkpoint_date >= date_from]
        if date_to:
            all_checkpoints = [c for c in all_checkpoints if c.checkpoint_date <= date_to]
        if tags:
            all_checkpoints = [
                c for c in all_checkpoints
                if all(t in c.tags for t in tags)
            ]

        all_checkpoints.sort(key=lambda c: c.checkpoint_date, reverse=True)
        total = len(all_checkpoints)
        offset = (page - 1) * page_size
        return all_checkpoints[offset:offset + page_size], total

    async def update(
        self,
        checkpoint: ProgressCheckpoint,
        *,
        checkpoint_date: date | None = None,
        weight_kg: float | None = None,
        body_fat_percentage: float | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> ProgressCheckpoint:
        if checkpoint_date is not None:
            checkpoint.checkpoint_date = checkpoint_date
        if weight_kg is not None:
            checkpoint.weight_kg = weight_kg
        if body_fat_percentage is not None:
            checkpoint.body_fat_percentage = body_fat_percentage
        if notes is not None:
            checkpoint.notes = notes
        if tags is not None:
            checkpoint.tags = tags
        checkpoint.updated_at = datetime.now(dt_timezone.utc)
        await checkpoint.save()
        return checkpoint

    async def soft_delete(self, checkpoint: ProgressCheckpoint) -> None:
        checkpoint.is_deleted = True
        checkpoint.updated_at = datetime.now(dt_timezone.utc)
        await checkpoint.save()

    # ── Photos ─────────────────────────────────────────────────────────────────

    async def add_photo(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
        storage_key: str,
        file_size_bytes: int,
        width_px: int,
        height_px: int,
        original_filename: str | None = None,
        label: str | None = None,
    ) -> ProgressPhoto:
        """Add a photo to a checkpoint. display_order = existing count."""
        existing_count = await ProgressPhoto.find(
            ProgressPhoto.checkpoint_id == checkpoint_id
        ).count()

        photo = ProgressPhoto(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            storage_key=storage_key,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            width_px=width_px,
            height_px=height_px,
            display_order=existing_count,
            label=label,
        )
        await photo.insert()
        return photo

    async def get_photo_by_id(
        self,
        photo_id: UUID,
        user_id: UUID,
    ) -> ProgressPhoto | None:
        return await ProgressPhoto.find_one(
            ProgressPhoto.id == photo_id,
            ProgressPhoto.user_id == user_id,
        )

    async def delete_photo(self, photo: ProgressPhoto) -> None:
        """Hard delete the photo record."""
        await photo.delete()

    async def get_primary_photo(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
    ) -> ProgressPhoto | None:
        """Get the primary (display_order=0) photo for a checkpoint."""
        photos = await ProgressPhoto.find(
            ProgressPhoto.checkpoint_id == checkpoint_id,
            ProgressPhoto.user_id == user_id,
        ).to_list()
        if not photos:
            return None
        photos.sort(key=lambda p: p.display_order)
        return photos[0]

    async def get_photos_for_checkpoint(
        self,
        checkpoint_id: UUID,
    ) -> list[ProgressPhoto]:
        """Get all photos for a checkpoint, ordered by display_order."""
        photos = await ProgressPhoto.find(
            ProgressPhoto.checkpoint_id == checkpoint_id
        ).to_list()
        photos.sort(key=lambda p: p.display_order)
        return photos
