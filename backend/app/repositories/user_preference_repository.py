"""
UserPreference repository — data access for the user_preferences collection.
"""
from uuid import UUID

from app.models.user_preference import UserPreference
from app.repositories.base import BaseRepository


class UserPreferenceRepository(BaseRepository[UserPreference]):
    def __init__(self) -> None:
        super().__init__(UserPreference)

    async def get_or_create(self, user_id: UUID) -> UserPreference:
        """Fetch the user's preference document, creating a default one if missing."""
        pref = await UserPreference.find_one(UserPreference.user_id == user_id)
        if pref is None:
            pref = UserPreference(user_id=user_id)
            await pref.insert()
        return pref

    async def update(
        self,
        pref: UserPreference,
        *,
        preferred_report_style: str | None = None,
        report_enabled: bool | None = None,
    ) -> UserPreference:
        """Update preference fields — skips None values."""
        if preferred_report_style is not None:
            pref.preferred_report_style = preferred_report_style
        if report_enabled is not None:
            pref.report_enabled = report_enabled
        await pref.save_with_ts()
        return pref
