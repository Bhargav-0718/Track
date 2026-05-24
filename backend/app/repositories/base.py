"""
Generic async repository base class.

Pattern: Repository handles all SQL. Services handle all business logic.
Repositories never raise business exceptions — only let DB errors propagate.

Type parameters:
- ModelT: The SQLAlchemy ORM model
- CreateSchemaT: The Pydantic schema for creation
- UpdateSchemaT: The Pydantic schema for updates
"""
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic CRUD repository for SQLAlchemy async models.

    Subclasses should override:
    - model: the ORM class
    - Specific query methods (get_by_user, filter_by_date, etc.)
    """

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        """Fetch a record by primary key. Returns None if not found."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, id: UUID, user_id: UUID) -> ModelT | None:
        """
        Fetch a record by PK, scoped to a specific user.
        Prevents cross-user data access.
        """
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == id,  # type: ignore[attr-defined]
                self.model.user_id == user_id,  # type: ignore[attr-defined]
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        order_by: Any = None,
    ) -> list[ModelT]:
        """List all records with pagination."""
        query = select(self.model)
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """Count all records."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        """
        Create a new record from keyword arguments.
        Caller must commit the session.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()   # Flush to get the DB-generated ID
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """
        Update an existing instance with keyword arguments.
        Caller must commit the session.
        """
        for key, value in kwargs.items():
            if value is not None or key in kwargs:
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """
        Hard delete a record.
        Prefer soft_delete() for audit-trail models.
        """
        await self.session.delete(instance)
        await self.session.flush()

    async def soft_delete(self, instance: ModelT) -> ModelT:
        """
        Soft delete — sets is_deleted=True.
        Only works on models with SoftDeleteMixin.
        """
        instance.is_deleted = True  # type: ignore[attr-defined]
        await self.session.flush()
        return instance

    async def save(self, instance: ModelT) -> ModelT:
        """Add an unsaved instance to the session and flush."""
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
