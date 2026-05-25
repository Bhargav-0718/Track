"""
StepLog document.

One document per user per day — upserted so today's entry is always current.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from pymongo import ASCENDING

from app.models.base import BaseDocument


class StepLog(BaseDocument):
    user_id: UUID
    date: date
    steps: int

    class Settings:
        name = "step_logs"
        indexes = [
            # Unique per user per date
            [("user_id", ASCENDING), ("date", ASCENDING)],
        ]

    def __repr__(self) -> str:
        return f"<StepLog user={self.user_id} date={self.date} steps={self.steps}>"
