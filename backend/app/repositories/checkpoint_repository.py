"""
CheckpointRepository — data access for progress checkpoints and photos.

Handles:
- CRUD on ProgressCheckpoint
- Photo attachment/removal
- Listing with pagination and filtering
- Photo primary selection for comparison endpoint
"""
from datetime import date
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.progress_checkpoint import ProgressCheckpoint
from app.models.progress_photo import ProgressPhoto


class CheckpointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
        self.session.add(checkpoint)
        await self.session.flush()
        return checkpoint

    async def get_by_id_for_user(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
        load_photos: bool = True,
    ) -> ProgressCheckpoint | None:
        """Fetch a checkpoint with optional eager-loaded photos."""
        stmt = select(ProgressCheckpoint).where(
            and_(
                ProgressCheckpoint.id == checkpoint_id,
                ProgressCheckpoint.user_id == user_id,
                ProgressCheckpoint.is_deleted.is_(False),
            )
        )
        if load_photos:
            stmt = stmt.options(selectinload(ProgressCheckpoint.photos))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
        filters = [
            ProgressCheckpoint.user_id == user_id,
            ProgressCheckpoint.is_deleted.is_(False),
        ]
        if date_from:
            filters.append(ProgressCheckpoint.checkpoint_date >= date_from)
        if date_to:
            filters.append(ProgressCheckpoint.checkpoint_date <= date_to)
        if tags:
            # Filter checkpoints that have ALL specified tags
            for tag in tags:
                filters.append(ProgressCheckpoint.tags.contains([tag]))

        # Total count
        count_stmt = select(func.count(ProgressCheckpoint.id)).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Data with primary photo
        offset = (page - 1) * page_size
        stmt = (
            select(ProgressCheckpoint)
            .where(and_(*filters))
            .order_by(desc(ProgressCheckpoint.checkpoint_date))
            .offset(offset)
            .limit(page_size)
            .options(selectinload(ProgressCheckpoint.photos))
        )
        result = await self.session.execute(stmt)
        checkpoints = list(result.scalars().all())

        return checkpoints, total

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
        await self.session.flush()
        return checkpoint

    async def soft_delete(self, checkpoint: ProgressCheckpoint) -> None:
        checkpoint.is_deleted = True
        await self.session.flush()

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
        """
        Add a photo to a checkpoint.
        display_order is auto-assigned as max existing + 1.
        """
        # Get current max display_order for this checkpoint
        count_stmt = select(func.count(ProgressPhoto.id)).where(
            ProgressPhoto.checkpoint_id == checkpoint_id
        )
        existing_count = (await self.session.execute(count_stmt)).scalar_one()

        photo = ProgressPhoto(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            storage_key=storage_key,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            width_px=width_px,
            height_px=height_px,
            display_order=existing_count,   # 0-indexed
            label=label,
        )
        self.session.add(photo)
        await self.session.flush()
        return photo

    async def get_photo_by_id(
        self,
        photo_id: UUID,
        user_id: UUID,
    ) -> ProgressPhoto | None:
        stmt = select(ProgressPhoto).where(
            and_(
                ProgressPhoto.id == photo_id,
                ProgressPhoto.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_photo(self, photo: ProgressPhoto) -> None:
        """Hard delete the photo record (actual file deletion is handled by StorageBackend)."""
        await self.session.delete(photo)
        await self.session.flush()

    async def get_primary_photo(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
    ) -> ProgressPhoto | None:
        """Get the primary (display_order=0) photo for a checkpoint."""
        stmt = (
            select(ProgressPhoto)
            .where(
                and_(
                    ProgressPhoto.checkpoint_id == checkpoint_id,
                    ProgressPhoto.user_id == user_id,
                )
            )
            .order_by(ProgressPhoto.display_order)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
