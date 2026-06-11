"""
UserPreferenceService — business logic for AI/report preferences.
"""
from uuid import UUID

from app.repositories.user_preference_repository import UserPreferenceRepository
from app.schemas.user_preference import UserPreferenceResponse, UserPreferenceUpdate


class UserPreferenceService:
    def __init__(self) -> None:
        self.repo = UserPreferenceRepository()

    async def get(self, user_id: UUID) -> UserPreferenceResponse:
        pref = await self.repo.get_or_create(user_id)
        return UserPreferenceResponse.model_validate(pref)

    async def update(self, user_id: UUID, data: UserPreferenceUpdate) -> UserPreferenceResponse:
        pref = await self.repo.get_or_create(user_id)
        updated = await self.repo.update(
            pref,
            preferred_report_style=data.preferred_report_style,
            report_enabled=data.report_enabled,
        )
        return UserPreferenceResponse.model_validate(updated)
