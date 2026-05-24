"""
StorageBackend — abstract protocol for file storage.

Using typing.Protocol so we can swap local filesystem → S3 in Phase 4
without changing PhotoService at all. No ABC inheritance required.
"""
from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class StorageBackend(Protocol):
    """
    Abstract interface for binary file storage.

    Local implementation: LocalStorageBackend (saves to disk under uploads/)
    Future S3 implementation: S3StorageBackend (boto3, presigned URLs)
    """

    async def save(
        self,
        user_id: UUID,
        data: bytes,
        extension: str,
    ) -> str:
        """
        Persist file bytes and return a stable storage key (path or S3 key).

        The storage key is stored in the food_log.image_url column.
        It is NOT a public URL — use get_url() to resolve one.

        Args:
            user_id:   Owner of the file (used for path namespacing)
            data:      Raw file bytes
            extension: Lowercase extension without leading dot (e.g. "jpg")

        Returns:
            storage_key — opaque identifier for this file
        """
        ...

    async def get_url(self, storage_key: str) -> str:
        """
        Resolve a storage key to a publicly accessible URL.

        For local backend: /uploads/{path}
        For S3 backend: presigned URL or CloudFront URL
        """
        ...

    async def delete(self, storage_key: str) -> None:
        """
        Remove a file from storage. Best-effort — should not raise on missing file.
        """
        ...

    async def exists(self, storage_key: str) -> bool:
        """Return True if the file exists in storage."""
        ...
