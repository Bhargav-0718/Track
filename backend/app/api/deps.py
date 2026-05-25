"""
FastAPI dependency injection functions.

These are the shared dependencies used across all route handlers:
- get_current_user_id: Authenticated user UUID from JWT token
- get_current_user: Full user document from MongoDB

Design: Dependencies are thin — they extract from the request and delegate
to repositories for lookups. No business logic in deps.py.
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationError
from app.core.security import extract_user_id
from app.models.user import User
from app.repositories.user_repository import UserRepository

# ── HTTP Bearer Scheme ─────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


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
) -> User:
    """
    Get the full authenticated user from MongoDB.
    Use get_current_user_id when you only need the UUID (avoids extra DB query).
    """
    repo = UserRepository()
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
