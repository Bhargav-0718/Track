"""
CheckpointService — business logic for progress checkpoints.

Handles:
- Creating and managing checkpoints (date, weight, notes, tags)
- Photo upload pipeline: validate → compress → store → record
- AI physique comparison: fetch photos → send to GPT-4o → return structured result
- Cleaning up storage when photos/checkpoints are deleted

Image upload pipeline:
  1. validate_image()    — size and format check
  2. preprocess_image()  — resize to max 1024px, compress to JPEG
  3. storage.save()      — persist bytes, get storage_key
  4. checkpoint_repo.add_photo() — create ProgressPhoto record
  5. Return PhotoResponse with resolved URL
"""
from datetime import date
from uuid import UUID

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.core.logging import get_logger
from app.repositories.checkpoint_repository import CheckpointRepository
from app.schemas.checkpoint import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointSummary,
    CheckpointUpdate,
    CompareRequest,
    CompareResponse,
    PhysiqueObservation,
    PhotoResponse,
)
from app.services.ai.vision_service import (
    compare_physique,
    preprocess_image,
    validate_image,
)
from app.services.storage import get_storage_backend

logger = get_logger(__name__)


class CheckpointService:
    def __init__(self) -> None:
        self.repo = CheckpointRepository()
        self.storage = get_storage_backend()

    # ── Checkpoint CRUD ────────────────────────────────────────────────────────

    async def create_checkpoint(
        self,
        user_id: UUID,
        data: CheckpointCreate,
    ) -> CheckpointResponse:
        checkpoint = await self.repo.create(
            user_id=user_id,
            checkpoint_date=data.checkpoint_date,
            weight_kg=data.weight_kg,
            body_fat_percentage=data.body_fat_percentage,
            notes=data.notes,
            tags=data.tags,
        )

        logger.info(
            "checkpoint_created",
            checkpoint_id=str(checkpoint.id),
            user_id=str(user_id),
            date=str(data.checkpoint_date),
            weight=data.weight_kg,
        )

        return CheckpointResponse(
            id=checkpoint.id,
            checkpoint_date=checkpoint.checkpoint_date,
            weight_kg=checkpoint.weight_kg,
            body_fat_percentage=checkpoint.body_fat_percentage,
            notes=checkpoint.notes,
            tags=checkpoint.tags,
            photos=[],
            created_at=checkpoint.created_at,
            updated_at=checkpoint.updated_at,
        )

    async def get_checkpoint(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
    ) -> CheckpointResponse:
        checkpoint = await self.repo.get_by_id_for_user(checkpoint_id, user_id, load_photos=True)
        if not checkpoint:
            raise ResourceNotFoundError(
                message=f"Checkpoint {checkpoint_id} not found",
                resource_type="ProgressCheckpoint",
                resource_id=str(checkpoint_id),
            )
        return await self._to_response(checkpoint)

    async def list_checkpoints(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        date_from: date | None = None,
        date_to: date | None = None,
        tags: list[str] | None = None,
    ) -> tuple[list[CheckpointSummary], int]:
        checkpoints, total = await self.repo.list_for_user(
            user_id,
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
            tags=tags,
        )
        summaries = []
        for cp in checkpoints:
            # Fetch photos for each checkpoint summary
            from app.repositories.checkpoint_repository import CheckpointRepository
            photos = await self.repo.get_photos_for_checkpoint(cp.id)
            primary_url = None
            if photos:
                primary_url = await self.storage.get_url(photos[0].storage_key)

            summaries.append(CheckpointSummary(
                id=cp.id,
                checkpoint_date=cp.checkpoint_date,
                weight_kg=cp.weight_kg,
                body_fat_percentage=cp.body_fat_percentage,
                notes=cp.notes,
                tags=cp.tags,
                photo_count=len(photos),
                primary_photo_url=primary_url,
                created_at=cp.created_at,
            ))

        return summaries, total

    async def update_checkpoint(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
        data: CheckpointUpdate,
    ) -> CheckpointResponse:
        checkpoint = await self.repo.get_by_id_for_user(checkpoint_id, user_id, load_photos=True)
        if not checkpoint:
            raise ResourceNotFoundError(
                message=f"Checkpoint {checkpoint_id} not found",
                resource_type="ProgressCheckpoint",
                resource_id=str(checkpoint_id),
            )

        checkpoint = await self.repo.update(
            checkpoint,
            checkpoint_date=data.checkpoint_date,
            weight_kg=data.weight_kg,
            body_fat_percentage=data.body_fat_percentage,
            notes=data.notes,
            tags=data.tags,
        )
        return await self._to_response(checkpoint)

    async def delete_checkpoint(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
    ) -> None:
        checkpoint = await self.repo.get_by_id_for_user(checkpoint_id, user_id, load_photos=True)
        if not checkpoint:
            raise ResourceNotFoundError(
                message=f"Checkpoint {checkpoint_id} not found",
                resource_type="ProgressCheckpoint",
                resource_id=str(checkpoint_id),
            )

        # Delete photos from storage before soft-deleting the record
        photos = await self.repo.get_photos_for_checkpoint(checkpoint_id)
        for photo in photos:
            await self.storage.delete(photo.storage_key)

        await self.repo.soft_delete(checkpoint)

        logger.info(
            "checkpoint_deleted",
            checkpoint_id=str(checkpoint_id),
            photos_removed=len(photos),
        )

    # ── Photo Management ───────────────────────────────────────────────────────

    async def upload_photo(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
        image_bytes: bytes,
        original_filename: str | None = None,
        label: str | None = None,
    ) -> PhotoResponse:
        """
        Full photo upload pipeline:
          validate → compress → store → create DB record → return response
        """
        # Verify checkpoint ownership
        checkpoint = await self.repo.get_by_id_for_user(
            checkpoint_id, user_id, load_photos=False
        )
        if not checkpoint:
            raise ResourceNotFoundError(
                message=f"Checkpoint {checkpoint_id} not found",
                resource_type="ProgressCheckpoint",
                resource_id=str(checkpoint_id),
            )

        # Validate raw image
        try:
            validate_image(image_bytes)
        except ValueError as e:
            raise ValidationError(message=str(e)) from e

        # Compress and resize
        jpeg_bytes, width, height = preprocess_image(image_bytes)

        # Save to storage
        storage_key = await self.storage.save(
            user_id=user_id,
            data=jpeg_bytes,
            extension="jpg",
        )

        # Create DB record
        photo = await self.repo.add_photo(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            storage_key=storage_key,
            file_size_bytes=len(jpeg_bytes),
            width_px=width,
            height_px=height,
            original_filename=original_filename,
            label=label,
        )

        url = await self.storage.get_url(storage_key)

        logger.info(
            "photo_uploaded",
            photo_id=str(photo.id),
            checkpoint_id=str(checkpoint_id),
            size_kb=round(len(jpeg_bytes) / 1024),
            dimensions=f"{width}x{height}",
        )

        return PhotoResponse(
            id=photo.id,
            checkpoint_id=checkpoint_id,
            url=url,
            original_filename=photo.original_filename,
            content_type=photo.content_type,
            file_size_bytes=photo.file_size_bytes,
            width_px=photo.width_px,
            height_px=photo.height_px,
            display_order=photo.display_order,
            label=photo.label,
            created_at=photo.created_at,
        )

    async def delete_photo(
        self,
        checkpoint_id: UUID,
        photo_id: UUID,
        user_id: UUID,
    ) -> None:
        """Delete a photo from storage and the database."""
        # Verify checkpoint ownership
        checkpoint = await self.repo.get_by_id_for_user(
            checkpoint_id, user_id, load_photos=False
        )
        if not checkpoint:
            raise ResourceNotFoundError(
                message=f"Checkpoint {checkpoint_id} not found",
                resource_type="ProgressCheckpoint",
                resource_id=str(checkpoint_id),
            )

        photo = await self.repo.get_photo_by_id(photo_id, user_id)
        if not photo or photo.checkpoint_id != checkpoint_id:
            raise ResourceNotFoundError(
                message=f"Photo {photo_id} not found",
                resource_type="ProgressPhoto",
                resource_id=str(photo_id),
            )

        storage_key = photo.storage_key
        await self.repo.delete_photo(photo)
        await self.storage.delete(storage_key)

        logger.info("photo_deleted", photo_id=str(photo_id), checkpoint_id=str(checkpoint_id))

    # ── AI Comparison ──────────────────────────────────────────────────────────

    async def compare_checkpoints(
        self,
        user_id: UUID,
        request: CompareRequest,
    ) -> CompareResponse:
        """
        Compare two checkpoints using GPT-4o multimodal analysis.

        Fetches the primary photo from each checkpoint, sends both to GPT-4o,
        and returns a structured physique comparison.

        Raises:
            ResourceNotFoundError if either checkpoint or their photos are missing
            ExternalServiceError if the AI call fails
        """
        # Fetch before checkpoint
        before_cp = await self.repo.get_by_id_for_user(
            request.before_checkpoint_id, user_id, load_photos=False
        )
        if not before_cp:
            raise ResourceNotFoundError(
                message=f"Before checkpoint {request.before_checkpoint_id} not found",
                resource_type="ProgressCheckpoint",
                resource_id=str(request.before_checkpoint_id),
            )

        # Fetch after checkpoint
        after_cp = await self.repo.get_by_id_for_user(
            request.after_checkpoint_id, user_id, load_photos=False
        )
        if not after_cp:
            raise ResourceNotFoundError(
                message=f"After checkpoint {request.after_checkpoint_id} not found",
                resource_type="ProgressCheckpoint",
                resource_id=str(request.after_checkpoint_id),
            )

        # Resolve photos (specific or primary)
        if request.before_photo_id:
            before_photo = await self.repo.get_photo_by_id(request.before_photo_id, user_id)
            if not before_photo or before_photo.checkpoint_id != request.before_checkpoint_id:
                raise ResourceNotFoundError(
                    message=f"Before photo {request.before_photo_id} not found",
                    resource_type="ProgressPhoto",
                    resource_id=str(request.before_photo_id),
                )
        else:
            before_photo = await self.repo.get_primary_photo(
                request.before_checkpoint_id, user_id
            )

        if request.after_photo_id:
            after_photo = await self.repo.get_photo_by_id(request.after_photo_id, user_id)
            if not after_photo or after_photo.checkpoint_id != request.after_checkpoint_id:
                raise ResourceNotFoundError(
                    message=f"After photo {request.after_photo_id} not found",
                    resource_type="ProgressPhoto",
                    resource_id=str(request.after_photo_id),
                )
        else:
            after_photo = await self.repo.get_primary_photo(request.after_checkpoint_id, user_id)

        if not before_photo:
            raise ValidationError(
                message="The 'before' checkpoint has no photos. Upload a photo first."
            )
        if not after_photo:
            raise ValidationError(
                message="The 'after' checkpoint has no photos. Upload a photo first."
            )

        # Read image bytes from storage
        before_path = await self._read_storage_file(before_photo.storage_key)
        after_path = await self._read_storage_file(after_photo.storage_key)

        # Call GPT-4o
        analysis = await compare_physique(
            before_image_bytes=before_path,
            after_image_bytes=after_path,
            before_date=before_cp.checkpoint_date,
            after_date=after_cp.checkpoint_date,
        )

        days_elapsed = (after_cp.checkpoint_date - before_cp.checkpoint_date).days
        weight_delta = None
        if before_cp.weight_kg and after_cp.weight_kg:
            weight_delta = round(after_cp.weight_kg - before_cp.weight_kg, 2)

        return CompareResponse(
            before_checkpoint_id=request.before_checkpoint_id,
            after_checkpoint_id=request.after_checkpoint_id,
            before_date=before_cp.checkpoint_date,
            after_date=after_cp.checkpoint_date,
            days_elapsed=days_elapsed,
            weight_delta_kg=weight_delta,
            overall_summary=analysis.overall_summary,
            observations=[
                PhysiqueObservation(
                    category=obs.category,
                    observation=obs.observation,
                    direction=obs.direction,
                )
                for obs in analysis.observations
            ],
            encouragement=analysis.encouragement,
            confidence_note=analysis.confidence_note,
            overall_progress=analysis.overall_progress,
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _to_response(self, checkpoint) -> CheckpointResponse:
        """Convert Beanie document to response schema with resolved photo URLs."""
        photos_data = await self.repo.get_photos_for_checkpoint(checkpoint.id)
        photos = []
        for photo in photos_data:
            url = await self.storage.get_url(photo.storage_key)
            photos.append(PhotoResponse(
                id=photo.id,
                checkpoint_id=checkpoint.id,
                url=url,
                original_filename=photo.original_filename,
                content_type=photo.content_type,
                file_size_bytes=photo.file_size_bytes,
                width_px=photo.width_px,
                height_px=photo.height_px,
                display_order=photo.display_order,
                label=photo.label,
                created_at=photo.created_at,
            ))

        return CheckpointResponse(
            id=checkpoint.id,
            checkpoint_date=checkpoint.checkpoint_date,
            weight_kg=checkpoint.weight_kg,
            body_fat_percentage=checkpoint.body_fat_percentage,
            notes=checkpoint.notes,
            tags=checkpoint.tags,
            photos=photos,
            created_at=checkpoint.created_at,
            updated_at=checkpoint.updated_at,
        )

    async def _read_storage_file(self, storage_key: str) -> bytes:
        """Read file bytes from local storage for sending to vision API."""
        from pathlib import Path
        from app.config import settings

        root = Path(settings.storage_local_root).resolve()
        file_path = (root / storage_key).resolve()

        # Path traversal guard
        if not str(file_path).startswith(str(root)):
            raise ValueError(f"Path traversal detected: {storage_key}")

        with open(str(file_path), "rb") as f:
            return f.read()
