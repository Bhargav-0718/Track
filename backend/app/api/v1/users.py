"""
User and authentication endpoints.

Routes:
  POST /auth/register   → Create account + return JWT
  POST /auth/login      → Authenticate + return JWT
  GET  /users/me        → Get current user profile
  PUT  /users/me        → Update current user profile
"""
from fastapi import APIRouter, status

from app.api.deps import CurrentUser, CurrentUserID
from app.schemas.user import AuthResponse, LoginRequest, UserCreate, UserProfile, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    tags=["auth"],
)
async def register(
    data: UserCreate,
) -> AuthResponse:
    """
    Register a new user account.

    Returns a JWT access token immediately — no email verification in Phase 1.
    """
    service = UserService()
    return await service.register(data)


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="Authenticate with email and password",
    tags=["auth"],
)
async def login(
    data: LoginRequest,
) -> AuthResponse:
    """Authenticate and receive a JWT access token."""
    service = UserService()
    return await service.login(data)


@router.get(
    "/users/me",
    response_model=UserProfile,
    summary="Get current user profile",
    tags=["users"],
)
async def get_my_profile(
    current_user: CurrentUser,
) -> UserProfile:
    """Get the authenticated user's profile."""
    return UserProfile.model_validate(current_user)


@router.put(
    "/users/me",
    response_model=UserProfile,
    summary="Update current user profile",
    tags=["users"],
)
async def update_my_profile(
    data: UserUpdate,
    current_user_id: CurrentUserID,
) -> UserProfile:
    """
    Update user profile fields.

    If physical stats (weight, height, age) are updated and no manual
    calorie target exists, the system will auto-calculate TDEE.
    """
    service = UserService()
    return await service.update_profile(current_user_id, data)
