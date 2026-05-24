"""
Security utilities: JWT creation/verification, password hashing.

Phase 1: Full implementation — JWT auth is active from Day 1.
This prevents a painful retrofit in Phase 2 when memory is user-scoped.
"""
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import AuthenticationError

# ── Password Hashing ──────────────────────────────────────────────────────────
# Use bcrypt directly — passlib 1.7 is incompatible with bcrypt 5.x because
# bcrypt 5 removed __about__ and now rejects passwords >72 bytes in its
# internal wrap-bug detection path that passlib triggers.

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

class TokenPayload(BaseModel):
    sub: str           # user_id as string
    exp: datetime
    iat: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int    # seconds


def create_access_token(user_id: UUID) -> TokenResponse:
    """
    Create a signed JWT access token for the given user.

    Token payload:
    - sub: user_id (UUID as string)
    - iat: issued at (UTC)
    - exp: expiry (UTC)
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def decode_access_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.
    Raises AuthenticationError on any failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
        )
    except JWTError as e:
        raise AuthenticationError(
            message="Invalid or expired authentication token",
            details={"error": str(e)},
        ) from e


def extract_user_id(token: str) -> UUID:
    """Extract and validate the user_id UUID from a JWT token."""
    payload = decode_access_token(token)
    try:
        return UUID(payload.sub)
    except ValueError as e:
        raise AuthenticationError(
            message="Token contains invalid user identifier",
        ) from e
