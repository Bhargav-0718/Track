"""
Test fixtures and configuration.

Uses a separate test database (track_test_db).
Each test gets a fresh transaction that's rolled back after the test — fast isolation.
"""
import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base

# ── Test Database Engine ───────────────────────────────────────────────────────

TEST_DATABASE_URL = settings.database_url.replace(
    "/track_db", "/track_test_db"
).replace(
    settings.database_url.split("/")[-1], "track_test_db"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Schema Setup ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for all tests in the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def create_tables():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        # Enable extensions
        await conn.execute(__import__("sqlalchemy").text(
            "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""
        ))
        await conn.execute(__import__("sqlalchemy").text(
            "CREATE EXTENSION IF NOT EXISTS \"vector\""
        ))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(create_tables) -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test database session using transaction rollback for isolation.
    Each test gets a clean state without dropping/recreating tables.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async test client with DB session override.
    """
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Test Data Factories ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user_data() -> dict:
    """Default test user data."""
    return {
        "email": f"test-{uuid4().hex[:8]}@example.com",
        "display_name": "Test User",
        "password": "testpassword123",
        "timezone": "UTC",
    }


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, test_user_data: dict) -> dict:
    """Register a test user and return the auth response."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
def auth_headers(registered_user: dict) -> dict:
    """Auth headers for an authenticated test user."""
    token = registered_user["access_token"]
    return {"Authorization": f"Bearer {token}"}
