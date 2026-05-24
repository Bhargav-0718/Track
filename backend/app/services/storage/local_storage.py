"""
LocalStorageBackend — saves files to the local filesystem.

Path structure:
    {root}/{user_id}/{YYYY}/{MM}/{uuid}.jpg

This gives per-user namespacing and date-based sharding so directories
don't grow too large. All processed images are JPEG regardless of input format.

For production with multiple users or significant storage needs,
swap this for S3StorageBackend (Phase 4+) without changing any callers —
the StorageBackend Protocol ensures interface compatibility.

File serving:
    FastAPI StaticFiles middleware serves {root}/ at /uploads/
    The public URL is: {storage_public_url_prefix}/{storage_key}
    e.g., /uploads/abc123.../2026/05/photo.jpg
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import aiofiles
import aiofiles.os

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalStorageBackend:
    """
    Stores files on the local filesystem.
    Compatible with the StorageBackend Protocol.
    """

    def __init__(self) -> None:
        self._root = Path(settings.storage_local_root).resolve()
        self._url_prefix = settings.storage_public_url_prefix.rstrip("/")

    def _key_to_path(self, storage_key: str) -> Path:
        """Resolve a storage key to an absolute filesystem path."""
        # Prevent path traversal attacks
        resolved = (self._root / storage_key).resolve()
        if not str(resolved).startswith(str(self._root)):
            raise ValueError(f"Path traversal detected: {storage_key}")
        return resolved

    async def save(
        self,
        user_id: UUID,
        data: bytes,
        extension: str,
    ) -> str:
        """
        Save bytes to local filesystem and return the storage key.

        Storage key format: {user_id}/{year}/{month}/{uuid}.{ext}
        This is relative to the storage root — never an absolute path.
        """
        now = datetime.now(timezone.utc)
        year = now.strftime("%Y")
        month = now.strftime("%m")
        filename = f"{uuid.uuid4()}.{extension.lower().lstrip('.')}"

        # Build relative storage key
        storage_key = f"{user_id}/{year}/{month}/{filename}"
        file_path = self._key_to_path(storage_key)

        # Ensure directory exists
        await aiofiles.os.makedirs(str(file_path.parent), exist_ok=True)

        async with aiofiles.open(str(file_path), "wb") as f:
            await f.write(data)

        logger.info(
            "file_saved",
            storage_key=storage_key,
            size_bytes=len(data),
            user_id=str(user_id),
        )
        return storage_key

    async def get_url(self, storage_key: str) -> str:
        """
        Resolve storage key to a publicly accessible URL.
        FastAPI StaticFiles serves self._root at self._url_prefix.
        """
        return f"{self._url_prefix}/{storage_key}"

    async def delete(self, storage_key: str) -> None:
        """Delete a file. Logs a warning if the file doesn't exist — does not raise."""
        try:
            file_path = self._key_to_path(storage_key)
            await aiofiles.os.remove(str(file_path))
            logger.info("file_deleted", storage_key=storage_key)
        except FileNotFoundError:
            logger.warning("file_not_found_on_delete", storage_key=storage_key)
        except Exception as e:
            logger.error("file_delete_failed", storage_key=storage_key, error=str(e))

    async def exists(self, storage_key: str) -> bool:
        """Return True if the file exists on disk."""
        try:
            file_path = self._key_to_path(storage_key)
            return file_path.exists()
        except ValueError:
            return False
