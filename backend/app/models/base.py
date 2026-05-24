"""
SQLAlchemy 2.0 declarative base with shared mixins.

Design decisions:
- UUIDs as primary keys (server-generated via gen_random_uuid())
- All timestamps are timezone-aware (TIMESTAMPTZ)
- updated_at uses server-side triggers for correctness across all update paths
- Mixins are composable — models opt in to what they need
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key, server-generated."""
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        index=True,
    )


class TimestampMixin:
    """Adds created_at and updated_at timestamp columns."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Adds soft delete support.
    IMPORTANT: Repositories must filter is_deleted=False in all queries.
    Hard deletes are reserved for GDPR data erasure requests.
    """
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
