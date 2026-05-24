"""
Async SQLAlchemy database engine and session management.

Design decisions:
- asyncpg driver for maximum PostgreSQL async performance
- Connection pooling tuned for typical FastAPI workloads
- Session-per-request pattern via FastAPI dependency injection
- Explicit session lifecycle (no implicit commits)
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ── Engine ─────────────────────────────────────────────────────────────────────

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.database_echo,
    # Recycle connections every 30 min to avoid stale connections
    pool_recycle=1800,
    # Verify connection health before using from pool
    pool_pre_ping=True,
    # JSON serialization: use standard json for now
    json_serializer=None,
)

# ── Session Factory ─────────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (safer for async)
    autocommit=False,
    autoflush=False,
)


# ── Dependency ──────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically closed after the request completes.
    Callers are responsible for commit/rollback within their scope.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Health Check ────────────────────────────────────────────────────────────────

async def check_database_connection() -> bool:
    """Verify the database is reachable. Used in health check endpoint."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        return False
