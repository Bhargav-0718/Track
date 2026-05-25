"""
DailyReport — AI-generated nightly summary of the user's day.

Generated once per day. Includes calorie/macro summary, workout summary,
consistency score, AI narrative insights, and motivational message.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pymongo import ASCENDING

from app.models.base import BaseDocument


class DailyReport(BaseDocument):
    # ── References ────────────────────────────────────────────────────────────
    user_id: UUID
    report_date: date

    # ── Computed Metrics ──────────────────────────────────────────────────────
    calorie_summary: dict = {}
    workout_summary: dict = {}
    macro_summary: dict = {}
    consistency_score: float = 0.0
    streak_days: int = 0
    weekly_consistency: float = 0.0

    # ── AI-Generated Content ───────────────────────────────────────────────────
    insights_text: str | None = None
    motivation_message: str | None = None
    behavioral_observations: list = []

    # ── Report Style ───────────────────────────────────────────────────────────
    report_style: str = "motivational"
    generation_model: str = "gpt-4o-mini"

    # ── Engagement Tracking ───────────────────────────────────────────────────
    was_shown: bool = False
    shown_at: datetime | None = None
    user_rating: int | None = None

    class Settings:
        name = "daily_reports"
        indexes = [
            # Unique per user per date
            [("user_id", ASCENDING), ("report_date", ASCENDING)],
        ]

    def __repr__(self) -> str:
        return (
            f"<DailyReport id={self.id} "
            f"date={self.report_date} score={self.consistency_score:.2f}>"
        )
