"""
StepLog model.

One row per user per day — upserted (not appended) so today's entry is always current.
Stores raw step count; distance and calorie calculations happen on the client
using user profile data (weight, height).
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class StepLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "step_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_step_log_user_date"),
        Index("ix_step_logs_user_date", "user_id", "date"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="step_logs")

    def __repr__(self) -> str:
        return f"<StepLog user={self.user_id} date={self.date} steps={self.steps}>"
