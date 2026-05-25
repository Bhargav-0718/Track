"""
UserService — business logic for user management and authentication.
"""
from uuid import UUID

from app.core.exceptions import (
    AuthenticationError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
)
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import AuthResponse, LoginRequest, UserCreate, UserProfile, UserUpdate

logger = get_logger(__name__)

# ── TDEE Constants ─────────────────────────────────────────────────────────────

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

GOAL_ADJUSTMENTS = {
    "lose_weight": -500,
    "maintain": 0,
    "gain_muscle": +250,
    "improve_fitness": +100,
}


def calculate_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    activity_level: str,
    goal: str,
    *,
    gender: str = "other",
) -> float:
    """Calculate TDEE using Mifflin-St Jeor equation."""
    if gender == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    elif gender == "female":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 78

    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    tdee = bmr * multiplier
    goal_adj = GOAL_ADJUSTMENTS.get(goal, 0)
    return round(tdee + goal_adj)


class UserService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    async def register(self, data: UserCreate) -> AuthResponse:
        """Register a new user."""
        if await self.repo.email_exists(data.email):
            raise ResourceAlreadyExistsError(
                message=f"An account with email '{data.email}' already exists",
                resource_type="User",
            )

        hashed = hash_password(data.password)
        user = await self.repo.create_user(
            email=data.email,
            display_name=data.display_name,
            hashed_password=hashed,
            user_timezone=data.timezone,
        )

        logger.info("user_registered", user_id=str(user.id), email=user.email)

        token = create_access_token(user.id)
        return AuthResponse(
            user=UserProfile.model_validate(user),
            access_token=token.access_token,
            expires_in=token.expires_in,
        )

    async def login(self, data: LoginRequest) -> AuthResponse:
        """Authenticate user by email + password."""
        user = await self.repo.get_by_email(data.email)

        if not user or not user.hashed_password:
            raise AuthenticationError(message="Invalid email or password")

        if not verify_password(data.password, user.hashed_password):
            logger.warning("login_failed", email=data.email)
            raise AuthenticationError(message="Invalid email or password")

        if not user.is_active:
            raise AuthenticationError(message="Account is deactivated")

        logger.info("user_logged_in", user_id=str(user.id))

        token = create_access_token(user.id)
        return AuthResponse(
            user=UserProfile.model_validate(user),
            access_token=token.access_token,
            expires_in=token.expires_in,
        )

    async def get_profile(self, user_id: UUID) -> UserProfile:
        """Get user profile."""
        user = await self.repo.get_active_user(user_id)
        if not user:
            raise ResourceNotFoundError(
                message=f"User {user_id} not found",
                resource_type="User",
                resource_id=str(user_id),
            )
        return UserProfile.model_validate(user)

    async def update_profile(self, user_id: UUID, data: UserUpdate) -> UserProfile:
        """Update user profile fields."""
        user = await self.repo.get_active_user(user_id)
        if not user:
            raise ResourceNotFoundError(
                message=f"User {user_id} not found",
                resource_type="User",
                resource_id=str(user_id),
            )

        updated = await self.repo.update_profile(
            user,
            display_name=data.display_name,
            user_timezone=data.timezone,
            age=data.age,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            activity_level=data.activity_level,
            goal=data.goal,
            target_calories=data.target_calories,
            target_protein_g=data.target_protein_g,
            target_carbs_g=data.target_carbs_g,
            target_fat_g=data.target_fat_g,
            gender=data.gender,
            daily_steps_target=data.daily_steps_target,
        )

        # Auto-calculate targets if physical stats were updated
        if any([data.weight_kg, data.height_cm, data.age, data.activity_level, data.goal]):
            await self._recalculate_targets_if_complete(updated)

        logger.info("user_profile_updated", user_id=str(user_id))
        return UserProfile.model_validate(updated)

    async def _recalculate_targets_if_complete(self, user: User) -> None:
        """Auto-calculate calorie target from TDEE if user has enough data."""
        if (user.weight_kg and user.height_cm and user.age and
                user.target_calories is None):
            tdee = calculate_tdee(
                weight_kg=user.weight_kg,
                height_cm=user.height_cm,
                age=user.age,
                activity_level=user.activity_level,
                goal=user.goal,
                gender=user.gender or "other",
            )
            user.target_calories = float(tdee)
            protein_factor = 1.2 if user.goal == "gain_muscle" else 0.9
            user.target_protein_g = round(user.weight_kg * protein_factor)
            await user.save()

            logger.info(
                "tdee_calculated",
                user_id=str(user.id),
                tdee=tdee,
                goal=user.goal,
            )

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Internal method — returns document. Use get_profile for API responses."""
        user = await self.repo.get_active_user(user_id)
        if not user:
            raise ResourceNotFoundError(
                message=f"User {user_id} not found",
                resource_type="User",
                resource_id=str(user_id),
            )
        return user
