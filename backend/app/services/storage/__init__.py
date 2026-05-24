"""
Storage backend factory.

Returns a singleton instance of the configured StorageBackend.
Add S3StorageBackend here when ready for cloud deployment.
"""
from functools import lru_cache

from app.config import settings
from app.services.storage.base import StorageBackend
from app.services.storage.local_storage import LocalStorageBackend


@lru_cache(maxsize=1)
def get_storage_backend() -> StorageBackend:
    """
    Return the configured storage backend (singleton).

    Current backends:
      "local" → LocalStorageBackend (saves to {storage_local_root}/)
      "s3"    → S3StorageBackend (Phase 4+, not yet implemented)
    """
    backend = settings.storage_backend

    if backend == "local":
        return LocalStorageBackend()  # type: ignore[return-value]

    raise NotImplementedError(
        f"Storage backend '{backend}' is not implemented yet. "
        "Supported backends: local"
    )
