"""
User request/response schemas.

Separation of concerns:
- UserCreate: what's needed to register (email, password, name)
- UserUpdate: what can be changed (everything except email for now)
- UserProfile: what the client receives (never expose hashed_password)
- UserPublic: minimal public representation (for logging context)
"""
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import ActivityLevel, FitnessGoal, TrackBaseSchema


# ── Request Schemas ────────────────────────────────────────────────────────────

class UserCreate(TrackBaseSchema):
    """Body for POST /api/v1/users/ (registration)."""
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        import zoneinfo
        try:
            zoneinfo.ZoneInfo(v)
        except Exception:
            raise ValueError(f"Invalid timezone: {v}")
        return v


class UserUpdate(TrackBaseSchema):
    """Body for PUT /api/v1/users/{user_id} — all fields optional."""
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    timezone: str | None = Field(default=None, max_length=50)
    age: int | None = Field(default=None, ge=10, le=120)
    height_cm: float | None = Field(default=None, ge=50.0, le=300.0)
    weight_kg: float | None = Field(default=None, ge=20.0, le=500.0)
    gender: str | None = Field(default=None, pattern="^(male|female|other)$")
    activity_level: ActivityLevel | None = None
    goal: FitnessGoal | None = None
    target_calories: float | None = Field(default=None, ge=500.0, le=10000.0)
    target_protein_g: float | None = Field(default=None, ge=0.0, le=1000.0)
    target_carbs_g: float | None = Field(default=None, ge=0.0, le=2000.0)
    target_fat_g: float | None = Field(default=None, ge=0.0, le=500.0)
    daily_steps_target: int | None = Field(default=None, ge=1000, le=100000)


class UserTargetsUpdate(TrackBaseSchema):
    """Specialized update for recalculating nutrition targets."""
    activity_level: ActivityLevel
    goal: FitnessGoal
    # If null, system calculates from TDEE formula
    override_calories: float | None = Field(default=None, ge=500.0, le=10000.0)


# ── Response Schemas ───────────────────────────────────────────────────────────

class UserProfile(TrackBaseSchema):
    """Full user profile returned to authenticated user."""
    id: UUID
    email: str
    display_name: str
    timezone: str
    age: int | None
    height_cm: float | None
    weight_kg: float | None
    gender: str | None
    activity_level: str
    goal: str
    target_calories: float | None
    target_protein_g: float | None
    target_carbs_g: float | None
    target_fat_g: float | None
    daily_steps_target: int | None
    is_active: bool


class UserPublic(TrackBaseSchema):
    """Minimal public user info — used in nested responses."""
    id: UUID
    display_name: str


class AuthResponse(TrackBaseSchema):
    """Response from registration or login endpoints."""
    user: UserProfile
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(TrackBaseSchema):
    """Body for POST /api/v1/auth/login."""
    email: EmailStr
    password: str
