"""
User document — identity, physical stats, and fitness goals.
"""
from __future__ import annotations

from typing import Annotated

from beanie import Indexed
from pydantic import EmailStr

from app.models.base import BaseDocument


class User(BaseDocument):
    # ── Identity ──────────────────────────────────────────────────────────────
    email: Annotated[str, Indexed(unique=True)]
    display_name: str
    hashed_password: str | None = None

    # ── Profile ───────────────────────────────────────────────────────────────
    timezone: str = "UTC"
    age: int | None = None
    height_cm: float | None = None
    weight_kg: float | None = None

    # ── Goals ─────────────────────────────────────────────────────────────────
    # Valid: sedentary | light | moderate | active | very_active
    activity_level: str = "moderate"
    # Valid: lose_weight | maintain | gain_muscle | improve_fitness
    goal: str = "maintain"

    # ── Targets ───────────────────────────────────────────────────────────────
    target_calories: float | None = None
    target_protein_g: float | None = None
    target_carbs_g: float | None = None
    target_fat_g: float | None = None

    # ── Activity ──────────────────────────────────────────────────────────────
    gender: str | None = None  # 'male' | 'female' | 'other'
    daily_steps_target: int | None = 10000

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: bool = True

    class Settings:
        name = "users"

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
