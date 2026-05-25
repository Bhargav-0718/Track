"""
DailySummary — pre-aggregated daily nutrition and activity snapshot.

Updated every time a food_log or workout_log is created/updated/deleted.
Serves as the Health Connect sync anchor.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pymongo import ASCENDING

from app.models.base import BaseDocument


class DailySummary(BaseDocument):
    # ── References ────────────────────────────────────────────────────────────
    user_id: UUID
    date: date

    # ── Nutrition In ──────────────────────────────────────────────────────────
    total_calories_in: float = 0.0
    total_protein_g: float = 0.0
    total_carbs_g: float = 0.0
    total_fat_g: float = 0.0
    total_fiber_g: float = 0.0
    food_log_count: int = 0

    # ── Calories Out ──────────────────────────────────────────────────────────
    total_calories_out: float = 0.0
    workout_count: int = 0

    # ── Activity (Health Connect) ─────────────────────────────────────────────
    steps: int | None = None
    active_minutes: int | None = None
    activity_calories: float | None = None

    # ── Computed ──────────────────────────────────────────────────────────────
    net_calories: float | None = None

    # ── Health Connect Sync ───────────────────────────────────────────────────
    health_connect_synced: bool = False
    last_synced_at: datetime | None = None

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: str | None = None

    class Settings:
        name = "daily_summaries"
        indexes = [
            # Unique per user per date
            [("user_id", ASCENDING), ("date", ASCENDING)],
        ]

    def __repr__(self) -> str:
        return (
            f"<DailySummary id={self.id} user={self.user_id} "
            f"date={self.date} cal_in={self.total_calories_in}>"
        )
