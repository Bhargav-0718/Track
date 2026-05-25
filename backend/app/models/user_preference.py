"""
UserPreference — personalization settings and dietary context.

Stored as a separate collection (one-to-one with User) to keep users lean.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from beanie import Indexed

from app.models.base import BaseDocument


class UserPreference(BaseDocument):
    # ── References ────────────────────────────────────────────────────────────
    user_id: Annotated[UUID, Indexed(unique=True)]

    # ── Dietary ───────────────────────────────────────────────────────────────
    dietary_restrictions: list[str] = []
    cuisine_preferences: list[str] = []
    disliked_foods: list[str] = []

    # ── Reminders ─────────────────────────────────────────────────────────────
    logging_reminders: dict = {}
    reminders_enabled: bool = False

    # ── UI Preferences ────────────────────────────────────────────────────────
    default_meal_view: str = "daily"
    show_macros: bool = True
    calorie_display_format: str = "rounded"

    # ── Report Preferences ────────────────────────────────────────────────────
    preferred_report_style: str = "motivational"
    report_enabled: bool = True
    report_generation_time: str = "21:00"

    # ── Extensible Metadata ───────────────────────────────────────────────────
    metadata_: dict = {}

    class Settings:
        name = "user_preferences"

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id}>"
