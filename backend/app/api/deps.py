"""
FastAPI dependency injection functions.

These are the shared dependencies used across all route handlers:
- get_db: Async database session
- get_current_user: Authenticated user from JWT token
- get_current_user_id: Just the UUID (cheaper than full user lookup)

Design: Dependencies are thin — they extract from the request and delegate
to services for business logic. No business logic in deps.py.
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import extract_user_id
from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

# ── HTTP Bearer Scheme ─────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)

# ── Type Aliases for cleaner route signatures ──────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ── Auth Dependencies ──────────────────────────────────────────────────────────

async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UUID:
    """
    Extract and validate user_id from Bearer token.
    Raises HTTP 401 if token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return extract_user_id(credentials.credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: DbSession,
) -> User:
    """
    Get the full authenticated user from DB.
    Use get_current_user_id when you only need the UUID (avoids extra DB query).
    """
    repo = UserRepository(db)
    user = await repo.get_active_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated",
        )
    return user


# ── Annotated Types for DI ─────────────────────────────────────────────────────

CurrentUserID = Annotated[UUID, Depends(get_current_user_id)]
CurrentUser = Annotated[User, Depends(get_current_user)]
