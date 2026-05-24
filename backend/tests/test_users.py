"""
Tests for user registration, login, and profile management.
"""
import pytest
from httpx import AsyncClient


class TestRegistration:
    async def test_register_success(
        self,
        client: AsyncClient,
        test_user_data: dict,
    ) -> None:
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]
        assert "hashed_password" not in data["user"]

    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_user_data: dict,
    ) -> None:
        # Register once
        await client.post("/api/v1/auth/register", json=test_user_data)
        # Register again with same email
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 409

    async def test_register_invalid_email(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "display_name": "Test", "password": "pass12345"},
        )
        assert response.status_code == 422

    async def test_register_short_password(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "display_name": "Test", "password": "short"},
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(
        self,
        client: AsyncClient,
        registered_user: dict,
        test_user_data: dict,
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        registered_user: dict,
        test_user_data: dict,
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    async def test_login_unknown_email(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert response.status_code == 401


class TestProfile:
    async def test_get_profile(
        self,
        client: AsyncClient,
        registered_user: dict,
        auth_headers: dict,
    ) -> None:
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["user"]["email"]
        assert "hashed_password" not in data

    async def test_get_profile_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_update_profile(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={
                "display_name": "Updated Name",
                "age": 28,
                "height_cm": 175.0,
                "weight_kg": 75.0,
                "activity_level": "active",
                "goal": "gain_muscle",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"
        assert data["age"] == 28

    async def test_update_profile_auto_calculates_targets(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """When physical stats are set, TDEE should be auto-calculated."""
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={
                "age": 30,
                "height_cm": 180.0,
                "weight_kg": 80.0,
                "activity_level": "moderate",
                "goal": "maintain",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # TDEE should be auto-calculated (roughly 2600-2800 for these stats)
        assert data["target_calories"] is not None
        assert 1500 < data["target_calories"] < 4000
