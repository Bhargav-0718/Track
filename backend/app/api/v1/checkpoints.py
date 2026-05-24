"""
Progress checkpoint endpoints.

Routes:
  POST   /checkpoints/                           → Create checkpoint
  GET    /checkpoints/                           → List checkpoints (paginated)
  GET    /checkpoints/{id}                       → Get checkpoint with photos
  PATCH  /checkpoints/{id}                       → Update checkpoint metadata
  DELETE /checkpoints/{id}                       → Delete checkpoint + photos
  POST   /checkpoints/{id}/photos               → Upload photo to checkpoint
  DELETE /checkpoints/{id}/photos/{photo_id}    → Delete single photo
  POST   /checkpoints/compare                   → AI physique comparison
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, UploadFile, status, File, Form

from app.api.deps import CurrentUserID, DbSession
from app.schemas.checkpoint import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointSummary,
    CheckpointUpdate,
    CompareRequest,
    CompareResponse,
    PhotoResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.checkpoint_service import CheckpointService

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


@router.post(
    "/",
    response_model=CheckpointResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a progress checkpoint",
)
async def create_checkpoint(
    data: CheckpointCreate,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> CheckpointResponse:
    """
    Create a new progress checkpoint.

    A checkpoint captures your physique at a moment in time:
    - Date, weight, body fat % (all optional except date)
    - Notes and tags for filtering
    - Photos are added separately via POST /{id}/photos

    **Typical usage**: Create a checkpoint at the start/end of a training phase,
    then upload 1-4 photos (front/back/side), then compare with an earlier checkpoint.
    """
    service = CheckpointService(db)
    return await service.create_checkpoint(current_user_id, data)


@router.get(
    "/",
    response_model=PaginatedResponse[CheckpointSummary],
    summary="List progress checkpoints",
)
async def list_checkpoints(
    current_user_id: CurrentUserID,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: date | None = Query(default=None, description="Start date filter"),
    date_to: date | None = Query(default=None, description="End date filter"),
    tags: list[str] | None = Query(default=None, description="Filter by tags"),
) -> PaginatedResponse[CheckpointSummary]:
    """
    List checkpoints ordered by date (newest first).
    Each summary includes photo count and primary photo URL.
    """
    service = CheckpointService(db)
    checkpoints, total = await service.list_checkpoints(
        current_user_id,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        tags=tags,
    )
    return PaginatedResponse.create(
        items=checkpoints,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{checkpoint_id}",
    response_model=CheckpointResponse,
    summary="Get a checkpoint with all photos",
)
async def get_checkpoint(
    checkpoint_id: UUID,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> CheckpointResponse:
    """Get full checkpoint details including all photos with resolved URLs."""
    service = CheckpointService(db)
    return await service.get_checkpoint(checkpoint_id, current_user_id)


@router.patch(
    "/{checkpoint_id}",
    response_model=CheckpointResponse,
    summary="Update checkpoint metadata",
)
async def update_checkpoint(
    checkpoint_id: UUID,
    data: CheckpointUpdate,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> CheckpointResponse:
    """
    Update checkpoint metadata (weight, notes, tags, date).
    Photos are managed separately via the /photos sub-endpoints.
    All fields are optional — only provided fields are updated.
    """
    service = CheckpointService(db)
    return await service.update_checkpoint(checkpoint_id, current_user_id, data)


@router.delete(
    "/{checkpoint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a checkpoint and all its photos",
)
async def delete_checkpoint(
    checkpoint_id: UUID,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> None:
    """
    Delete a checkpoint. All associated photos are removed from storage.
    This action is irreversible.
    """
    service = CheckpointService(db)
    await service.delete_checkpoint(checkpoint_id, current_user_id)


@router.post(
    "/{checkpoint_id}/photos",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo to a checkpoint",
)
async def upload_photo(
    checkpoint_id: UUID,
    current_user_id: CurrentUserID,
    db: DbSession,
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WebP, HEIC)"),
    label: str | None = Form(
        default=None,
        description="Photo angle label: front, back, side-left, side-right"
    ),
) -> PhotoResponse:
    """
    Upload a photo to a checkpoint.

    **Image handling**:
    - Accepted formats: JPEG, PNG, WebP, HEIC
    - Maximum size: 20MB (raw upload)
    - Images are automatically resized to max 1024px and compressed to JPEG
    - Stored size will be significantly smaller than the original

    A checkpoint can have multiple photos (front, back, side views).
    The first uploaded photo becomes the primary thumbnail.
    """
    image_bytes = await file.read()
    service = CheckpointService(db)
    return await service.upload_photo(
        checkpoint_id=checkpoint_id,
        user_id=current_user_id,
        image_bytes=image_bytes,
        original_filename=file.filename,
        label=label,
    )


@router.delete(
    "/{checkpoint_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a photo from a checkpoint",
)
async def delete_photo(
    checkpoint_id: UUID,
    photo_id: UUID,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> None:
    """Delete a single photo from a checkpoint. Removes the file from storage."""
    service = CheckpointService(db)
    await service.delete_photo(checkpoint_id, photo_id, current_user_id)


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="AI physique comparison between two checkpoints",
)
async def compare_checkpoints(
    request: CompareRequest,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> CompareResponse:
    """
    Compare two progress checkpoints using GPT-4o multimodal AI.

    **Requirements**:
    - Both checkpoints must belong to the authenticated user
    - Both checkpoints must have at least one photo uploaded
    - The 'before' checkpoint should be earlier in date than 'after'

    **What the AI analyses**:
    - Visible fat distribution changes
    - Muscle definition changes (if visible)
    - Posture and body proportions
    - Waistline/midsection changes
    - Overall physique trajectory

    **Safety**:
    - This is fitness observation only, not medical advice
    - Results include an explicit disclaimer and confidence caveat
    - The AI will not make any medical claims or diagnoses

    **Note**: This endpoint calls GPT-4o vision and may take 10-20 seconds.
    """
    service = CheckpointService(db)
    return await service.compare_checkpoints(current_user_id, request)
