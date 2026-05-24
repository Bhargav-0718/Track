"""
Tests for food log creation, updating, correction, and daily summary.
"""
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


class TestFoodLogCreation:
    async def test_create_manual_log(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        response = await client.post(
            "/api/v1/food-logs/",
            headers=auth_headers,
            json={
                "food_name": "Dal Chawal",
                "calories": 420.0,
                "protein_g": 15.0,
                "carbs_g": 70.0,
                "fat_g": 8.0,
                "meal_type": "lunch",
                "portion_description": "medium bowl",
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["food_name"] == "Dal Chawal"
        assert data["calories"] == 420.0
        assert data["estimation_source"] == "manual"
        assert data["confidence_level"] == "confirmed"
        assert data["confidence_score"] == 1.0
        assert data["is_corrected"] is False

    async def test_create_log_with_raw_input_and_nutrition(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Quick log with both raw_input and nutrition values."""
        response = await client.post(
            "/api/v1/food-logs/",
            headers=auth_headers,
            json={
                "raw_input": "biryani half plate",
                "food_name": "Chicken Biryani",
                "calories": 380.0,
                "meal_type": "dinner",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["raw_input"] == "biryani half plate"

    async def test_create_log_missing_required_fields(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Should fail when neither raw_input nor food_name+calories provided."""
        response = await client.post(
            "/api/v1/food-logs/",
            headers=auth_headers,
            json={"meal_type": "lunch"},
        )
        assert response.status_code == 422

    async def test_create_log_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/food-logs/",
            json={"food_name": "Test", "calories": 100.0},
        )
        assert response.status_code == 401

    async def test_create_log_with_custom_timestamp(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Should allow logging food with a past timestamp."""
        past_time = "2024-01-15T08:30:00Z"
        response = await client.post(
            "/api/v1/food-logs/",
            headers=auth_headers,
            json={
                "food_name": "Oatmeal",
                "calories": 300.0,
                "meal_type": "breakfast",
                "logged_at": past_time,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "2024-01-15" in data["logged_at"]


class TestFoodLogRetrieval:
    async def test_get_food_log(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        # Create
        create_response = await client.post(
            "/api/v1/food-logs/",
            headers=auth_headers,
            json={"food_name": "Idli", "calories": 150.0, "meal_type": "breakfast"},
        )
        log_id = create_response.json()["id"]

        # Retrieve
        get_response = await client.get(
            f"/api/v1/food-logs/{log_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == log_id

    async def test_get_nonexistent_log(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        from uuid import uuid4
        response = await client.get(
            f"/api/v1/food-logs/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_list_food_logs(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        # Create multiple logs
        for food, cal in [("Rice", 200), ("Dal", 180), ("Roti", 120)]:
            await client.post(
                "/api/v1/food-logs/",
                headers=auth_headers,
                json={"food_name": food, "calories": cal, "meal_type": "lunch"},
            )

        response = await client.get("/api/v1/food-logs/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 3

    async def test_list_food_logs_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        response = await client.get(
            "/api/v1/food-logs/?page=1&page_size=2",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1


class TestFoodLogCorrection:
    async def test_correct_calories(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        # Create with estimated calories
        create_response = await client.post(
            "/api/v1/food-logs/",
            headers=auth_headers,
            json={"food_name": "Pasta", "calories": 400.0, "meal_type": "dinner"},
        )
        log_id = create_response.json()["id"]
        original_calories = create_response.json()["calories"]

        # Correct
        update_response = await client.put(
            f"/api/v1/food-logs/{log_id}",
            headers=auth_headers,
            json={"calories": 350.0},
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["calories"] == 350.0
        assert data["is_corrected"] is True
        assert data["original_calories"] == original_calories
        assert data["confidence_level"] == "confirmed"

    async def test_delete_food_log(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        create_response = await client.post(
            "/api/v1/food-logs/",
            headers=auth_headers,
            json={"food_name": "Snack", "calories": 100.0, "meal_type": "snack"},
        )
        log_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/api/v1/food-logs/{log_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Should no longer be retrievable
        get_response = await client.get(
            f"/api/v1/food-logs/{log_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


class TestDailySummary:
    async def test_get_daily_summary(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        # Log several items for today
        for food, cal in [("Breakfast", 400), ("Lunch", 600), ("Snack", 150)]:
            await client.post(
                "/api/v1/food-logs/",
                headers=auth_headers,
                json={"food_name": food, "calories": cal, "meal_type": "snack"},
            )

        from datetime import date
        today = date.today().isoformat()
        response = await client.get(
            f"/api/v1/food-logs/daily?date={today}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_calories"] >= 1150
        assert data["food_count"] >= 3
        assert len(data["logs"]) >= 3
