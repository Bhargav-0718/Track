"""
BehaviorEvent — lightweight engagement tracking for preference learning.

Records user interactions with generated content (reports, insights, etc.)
so the system can learn what style and content resonate with each user.

This is NOT full behavioral analytics — it's a simple event log.
Phase 4 analytics are computed by aggregating food_logs, workout_logs,
and daily_reports directly. BehaviorEvent tracks only explicit UI interactions.

Event types:
- report_viewed     : User opened a daily report
- report_rated      : User gave a thumbs up/down or star rating
- insight_dismissed : User dismissed an insight card
- insight_helpful   : User marked an insight as helpful
- streak_celebrated : User acknowledged a streak milestone notification
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class BehaviorEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "behavior_events"
    __table_args__ = (
        Index("ix_behavior_events_user_type", "user_id", "event_type"),
        # For time-range queries in analytics
        Index("ix_behavior_events_user_created", "user_id", "created_at"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Event Identity ─────────────────────────────────────────────────────────
    # e.g., "report_viewed", "report_rated", "insight_helpful"
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional reference to the entity this event is about
    # e.g., daily_report.id for report_viewed events
    entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    # e.g., "daily_report", "insight"
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Event Data ────────────────────────────────────────────────────────────
    # Flexible metadata depending on event_type:
    # report_rated:  {"rating": 4, "report_style": "motivational"}
    # insight_helpful: {"insight_text_hash": "abc123"}
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<BehaviorEvent id={self.id} "
            f"type={self.event_type} user={self.user_id}>"
        )
