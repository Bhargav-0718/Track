"""
UserService — business logic for user management and authentication.

Responsibilities:
- Registration with duplicate email check
- Login + token issuance
- Profile CRUD
- TDEE calculation for automatic calorie targets
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

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
    "lose_weight": -500,       # ~0.45 kg/week deficit
    "maintain": 0,
    "gain_muscle": +250,       # Lean bulk surplus
    "improve_fitness": +100,   # Slight surplus for performance
}


def calculate_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    activity_level: str,
    goal: str,
    *,
    is_male: bool = True,  # TODO: add sex to user profile in a future migration
) -> float:
    """
    Calculate Total Daily Energy Expenditure using Mifflin-St Jeor equation.

    This is an ESTIMATE, not medical advice. The system clearly communicates
    uncertainty to users (Phase 4: personalized target refinement from actual data).
    """
    # Mifflin-St Jeor BMR
    if is_male:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    tdee = bmr * multiplier

    goal_adj = GOAL_ADJUSTMENTS.get(goal, 0)
    return round(tdee + goal_adj)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def register(self, data: UserCreate) -> AuthResponse:
        """
        Register a new user.
        Raises ResourceAlreadyExistsError if email is taken.
        """
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
            timezone=data.timezone,
        )
        await self.session.commit()

        logger.info("user_registered", user_id=str(user.id), email=user.email)

        token = create_access_token(user.id)
        return AuthResponse(
            user=UserProfile.model_validate(user),
            access_token=token.access_token,
            expires_in=token.expires_in,
        )

    async def login(self, data: LoginRequest) -> AuthResponse:
        """
        Authenticate user by email + password.
        Raises AuthenticationError on failure (generic message — no email enumeration).
        """
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
        """Get user profile. Raises ResourceNotFoundError if not found."""
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
            timezone=data.timezone,
            age=data.age,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            activity_level=data.activity_level,
            goal=data.goal,
            target_calories=data.target_calories,
            target_protein_g=data.target_protein_g,
            target_carbs_g=data.target_carbs_g,
            target_fat_g=data.target_fat_g,
        )

        # Auto-calculate targets if physical stats were updated
        if (data.weight_kg or data.height_cm or data.age or
                data.activity_level or data.goal):
            await self._recalculate_targets_if_complete(updated)

        await self.session.commit()
        logger.info("user_profile_updated", user_id=str(user_id))
        return UserProfile.model_validate(updated)

    async def _recalculate_targets_if_complete(self, user: User) -> None:
        """
        If user has enough data (weight, height, age), auto-calculate
        calorie target using TDEE — but only if user hasn't set a manual override.
        """
        if (user.weight_kg and user.height_cm and user.age and
                user.target_calories is None):
            tdee = calculate_tdee(
                weight_kg=user.weight_kg,
                height_cm=user.height_cm,
                age=user.age,
                activity_level=user.activity_level,
                goal=user.goal,
            )
            user.target_calories = float(tdee)
            # Set default protein target (0.8-1.2g per kg based on goal)
            protein_factor = 1.2 if user.goal == "gain_muscle" else 0.9
            user.target_protein_g = round(user.weight_kg * protein_factor)

            logger.info(
                "tdee_calculated",
                user_id=str(user.id),
                tdee=tdee,
                goal=user.goal,
            )

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Internal method — returns ORM model. Use get_profile for API responses."""
        user = await self.repo.get_active_user(user_id)
        if not user:
            raise ResourceNotFoundError(
                message=f"User {user_id} not found",
                resource_type="User",
                resource_id=str(user_id),
            )
        return user
