"""
Test fixtures and configuration.

Uses a separate test database (track_test_db on the same Atlas cluster).
Each test session initialises Beanie once; individual tests are isolated
by using unique user IDs so documents don't bleed between tests.

Note: MongoDB has no transaction rollback for test isolation like SQL.
The approach here is:
  - Use a dedicated `track_test_db` database (set in pyproject.toml env vars)
  - Clean up collections after the test session via teardown
"""
import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import close_db, init_db
from app.main import app


# ── Event Loop ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for all tests in the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ── Database Lifecycle ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def init_test_db():
    """
    Initialise Beanie against the test database once per session.
    The test DB name (track_test_db) is set in pyproject.toml [tool.pytest.ini_options] env.
    """
    await init_db()
    yield
    # Drop all test collections after the full test session
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings
    client = AsyncIOMotorClient(settings.mongodb_url)
    await client.drop_database(settings.mongodb_db_name)
    client.close()
    await close_db()


# ── HTTP Client ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(init_test_db) -> AsyncGenerator[AsyncClient, None]:
    """Async test client wired to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── Test Data Factories ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user_data() -> dict:
    """Default test user data — unique email per test run."""
    return {
        "email": f"test-{uuid4().hex[:8]}@example.com",
        "display_name": "Test User",
        "password": "testpassword123",
        "timezone": "UTC",
    }


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, test_user_data: dict) -> dict:
    """Register a test user and return the full auth response dict."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
def auth_headers(registered_user: dict) -> dict:
    """Bearer auth headers for an authenticated test user."""
    token = registered_user["access_token"]
    return {"Authorization": f"Bearer {token}"}
