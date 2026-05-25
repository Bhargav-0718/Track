"""
User repository — data access for the users collection.
"""
from datetime import datetime
from datetime import timezone as dt_timezone
from uuid import UUID

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, email: str) -> User | None:
        """Case-insensitive email lookup."""
        return await User.find_one(User.email == email.lower().strip())

    async def email_exists(self, email: str) -> bool:
        """Check if an email address is already registered."""
        result = await User.find_one(User.email == email.lower().strip())
        return result is not None

    async def get_active_user(self, user_id: UUID) -> User | None:
        """Get a user only if their account is active."""
        return await User.find_one(User.id == user_id, User.is_active == True)

    async def create_user(
        self,
        email: str,
        display_name: str,
        hashed_password: str | None,
        user_timezone: str = "UTC",
    ) -> User:
        """Create a new user document."""
        user = User(
            email=email.lower().strip(),
            display_name=display_name,
            hashed_password=hashed_password,
            timezone=user_timezone,
        )
        await user.insert()
        return user

    async def update_profile(
        self,
        user: User,
        *,
        display_name: str | None = None,
        user_timezone: str | None = None,
        age: int | None = None,
        height_cm: float | None = None,
        weight_kg: float | None = None,
        activity_level: str | None = None,
        goal: str | None = None,
        target_calories: float | None = None,
        target_protein_g: float | None = None,
        target_carbs_g: float | None = None,
        target_fat_g: float | None = None,
        gender: str | None = None,
        daily_steps_target: int | None = None,
    ) -> User:
        """Update user profile fields — skips None values."""
        if display_name is not None:
            user.display_name = display_name
        if user_timezone is not None:
            user.timezone = user_timezone
        if age is not None:
            user.age = age
        if height_cm is not None:
            user.height_cm = height_cm
        if weight_kg is not None:
            user.weight_kg = weight_kg
        if activity_level is not None:
            user.activity_level = activity_level
        if goal is not None:
            user.goal = goal
        if target_calories is not None:
            user.target_calories = target_calories
        if target_protein_g is not None:
            user.target_protein_g = target_protein_g
        if target_carbs_g is not None:
            user.target_carbs_g = target_carbs_g
        if target_fat_g is not None:
            user.target_fat_g = target_fat_g
        if gender is not None:
            user.gender = gender
        if daily_steps_target is not None:
            user.daily_steps_target = daily_steps_target

        user.updated_at = datetime.now(dt_timezone.utc)
        await user.save()
        return user
