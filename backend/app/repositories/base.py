"""
Generic Beanie repository base class.

Pattern: Repository handles all DB queries. Services handle business logic.
No sessions needed — Beanie documents operate via the global Motor client.
"""
from typing import Any, Generic, TypeVar
from uuid import UUID

from beanie import Document

DocumentT = TypeVar("DocumentT", bound=Document)


class BaseRepository(Generic[DocumentT]):
    """
    Generic CRUD repository for Beanie async documents.

    Subclasses provide the document class and domain-specific queries.
    """

    def __init__(self, model: type[DocumentT]) -> None:
        self.model = model

    async def get_by_id(self, id: UUID) -> DocumentT | None:
        """Fetch a document by UUID primary key. Returns None if not found."""
        return await self.model.get(id)  # type: ignore[attr-defined]

    async def get_by_id_for_user(self, id: UUID, user_id: UUID) -> DocumentT | None:
        """Fetch a document by PK scoped to a specific user."""
        return await self.model.find_one(  # type: ignore[attr-defined]
            self.model.id == id,  # type: ignore[attr-defined]
            self.model.user_id == user_id,  # type: ignore[attr-defined]
        )

    async def list_all(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DocumentT]:
        """List all documents with pagination."""
        return await self.model.find_all().skip(offset).limit(limit).to_list()  # type: ignore[attr-defined]

    async def count_all(self) -> int:
        """Count all documents."""
        return await self.model.count()  # type: ignore[attr-defined]

    async def delete(self, instance: DocumentT) -> None:
        """Hard delete a document."""
        await instance.delete()

    async def soft_delete(self, instance: DocumentT) -> DocumentT:
        """Soft delete — sets is_deleted=True."""
        instance.is_deleted = True  # type: ignore[attr-defined]
        await instance.save()
        return instance
