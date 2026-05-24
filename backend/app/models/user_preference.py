"""
UserPreference — personalization settings and dietary context.

Stored separately from User to keep the users table lean.
Created automatically when a user completes onboarding.

These preferences feed into:
- Phase 2: Filter memory search results by dietary restrictions
- Phase 2: Bias calorie estimates for cuisine preferences
- Phase 4: Personalize reminders and motivation messages
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_preferences"

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Dietary ───────────────────────────────────────────────────────────────
    # e.g., ["vegetarian", "gluten_free", "dairy_free"]
    dietary_restrictions: Mapped[list] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    # e.g., ["indian", "mediterranean", "japanese"]
    cuisine_preferences: Mapped[list] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    # Foods to deprioritize in suggestions
    disliked_foods: Mapped[list] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )

    # ── Reminders ─────────────────────────────────────────────────────────────
    # {"breakfast": "08:00", "lunch": "13:00", "dinner": "19:00"}
    logging_reminders: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── UI Preferences ────────────────────────────────────────────────────────
    # Valid: daily | weekly | monthly
    default_meal_view: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)
    show_macros: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Valid: rounded | exact
    calorie_display_format: Mapped[str] = mapped_column(
        String(20), default="rounded", nullable=False
    )

    # ── Phase 4: Report Preferences ───────────────────────────────────────────
    # AI report style. Valid: motivational | analytical | brief | detailed
    preferred_report_style: Mapped[str] = mapped_column(
        String(20), default="motivational", nullable=False
    )
    # Whether nightly AI reports are enabled
    report_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Local time to generate the report (HH:MM, 24h). Evaluated against user.timezone.
    report_generation_time: Mapped[str] = mapped_column(
        String(10), default="21:00", nullable=False
    )

    # ── Extensible Metadata ───────────────────────────────────────────────────
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="preference", lazy="noload")

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id}>"
