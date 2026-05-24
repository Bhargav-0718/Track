"""
User repository — data access for the users table.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Case-insensitive email lookup."""
        result = await self.session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Check if an email address is already registered."""
        result = await self.session.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None

    async def get_active_user(self, user_id: UUID) -> User | None:
        """Get a user only if their account is active."""
        result = await self.session.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        display_name: str,
        hashed_password: str | None,
        timezone: str = "UTC",
    ) -> User:
        """Create a new user record."""
        return await self.create(
            email=email.lower().strip(),
            display_name=display_name,
            hashed_password=hashed_password,
            timezone=timezone,
        )

    async def update_profile(
        self,
        user: User,
        *,
        display_name: str | None = None,
        timezone: str | None = None,
        age: int | None = None,
        height_cm: float | None = None,
        weight_kg: float | None = None,
        activity_level: str | None = None,
        goal: str | None = None,
        target_calories: float | None = None,
        target_protein_g: float | None = None,
        target_carbs_g: float | None = None,
        target_fat_g: float | None = None,
    ) -> User:
        """Update user profile fields — skips None values."""
        updates: dict = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if timezone is not None:
            updates["timezone"] = timezone
        if age is not None:
            updates["age"] = age
        if height_cm is not None:
            updates["height_cm"] = height_cm
        if weight_kg is not None:
            updates["weight_kg"] = weight_kg
        if activity_level is not None:
            updates["activity_level"] = activity_level
        if goal is not None:
            updates["goal"] = goal
        if target_calories is not None:
            updates["target_calories"] = target_calories
        if target_protein_g is not None:
            updates["target_protein_g"] = target_protein_g
        if target_carbs_g is not None:
            updates["target_carbs_g"] = target_carbs_g
        if target_fat_g is not None:
            updates["target_fat_g"] = target_fat_g

        for key, value in updates.items():
            setattr(user, key, value)

        await self.session.flush()
        await self.session.refresh(user)
        return user
