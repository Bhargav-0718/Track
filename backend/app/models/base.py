"""
Beanie document base with shared mixins.

Design decisions:
- UUIDs as primary keys (client-generated via uuid4)
- All timestamps are timezone-aware UTC datetimes
- updated_at is updated by application code before each save
- Soft delete mixin adds is_deleted flag
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field


class BaseDocument(Document):
    """
    Base Beanie document with UUID primary key and timestamps.
    All models should inherit from this.
    """
    id: UUID = Field(default_factory=uuid4)  # type: ignore[assignment]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    async def save_with_ts(self) -> "BaseDocument":
        """Save the document, updating updated_at first."""
        self.updated_at = datetime.now(timezone.utc)
        await self.save()
        return self

    class Settings:
        use_revision = False
