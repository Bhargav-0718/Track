"""
BehaviorEvent — lightweight engagement tracking for preference learning.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field


class BehaviorEvent(Document):
    """Behavior events are immutable — no updated_at needed."""
    id: UUID = Field(default_factory=uuid4)  # type: ignore[assignment]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ── References ────────────────────────────────────────────────────────────
    user_id: UUID

    # ── Event Identity ─────────────────────────────────────────────────────────
    event_type: str
    entity_id: UUID | None = None
    entity_type: str | None = None

    # ── Event Data ────────────────────────────────────────────────────────────
    metadata_: dict = {}

    class Settings:
        name = "behavior_events"

    def __repr__(self) -> str:
        return (
            f"<BehaviorEvent id={self.id} "
            f"type={self.event_type} user={self.user_id}>"
        )
