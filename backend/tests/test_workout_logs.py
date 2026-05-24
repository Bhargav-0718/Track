"""
Tests for workout log creation, updating, and calorie estimation.
"""
import pytest
from httpx import AsyncClient


class TestWorkoutLogCreation:
    async def test_create_cardio_workout(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        response = await client.post(
            "/api/v1/workout-logs/",
            headers=auth_headers,
            json={
                "title": "Morning Run",
                "workout_type": "cardio",
                "duration_minutes": 30,
                "intensity": "moderate",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Morning Run"
        assert data["workout_type"] == "cardio"
        # Should have auto-estimated calories
        assert data["calories_burned"] is not None
        assert data["calories_burned"] > 0
        assert data["calories_source"] == "formula"

    async def test_create_strength_workout_with_exercises(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        response = await client.post(
            "/api/v1/workout-logs/",
            headers=auth_headers,
            json={
                "title": "Chest Day",
                "workout_type": "strength",
                "duration_minutes": 60,
                "intensity": "high",
                "exercises": [
                    {"name": "Bench Press", "sets": 4, "reps": 8, "weight_kg": 80.0},
                    {"name": "Incline Press", "sets": 3, "reps": 10, "weight_kg": 60.0},
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["exercises"]) == 2
        assert data["exercises"][0]["name"] == "Bench Press"

    async def test_create_workout_with_explicit_calories(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        response = await client.post(
            "/api/v1/workout-logs/",
            headers=auth_headers,
            json={
                "title": "Cycling",
                "workout_type": "cardio",
                "duration_minutes": 45,
                "intensity": "high",
                "calories_burned": 520.0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["calories_burned"] == 520.0
        assert data["calories_source"] == "manual"

    async def test_create_health_connect_workout(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Health Connect workouts should deduplicate by health_connect_id."""
        workout_data = {
            "title": "HC Walk",
            "workout_type": "cardio",
            "duration_minutes": 20,
            "intensity": "low",
            "health_connect_id": "hc-abc-123",
        }

        response1 = await client.post(
            "/api/v1/workout-logs/",
            headers=auth_headers,
            json=workout_data,
        )
        assert response1.status_code == 201
        id1 = response1.json()["id"]

        # Second sync with same ID should return existing, not create new
        response2 = await client.post(
            "/api/v1/workout-logs/",
            headers=auth_headers,
            json=workout_data,
        )
        assert response2.status_code == 201
        id2 = response2.json()["id"]

        assert id1 == id2  # Same record returned


class TestWorkoutCalorieEstimation:
    async def test_formula_estimation_cardio(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Cardio should produce higher calories than strength for same duration."""
        cardio_response = await client.post(
            "/api/v1/workout-logs/",
            headers=auth_headers,
            json={
                "title": "Run",
                "workout_type": "cardio",
                "duration_minutes": 30,
                "intensity": "moderate",
            },
        )

        strength_response = await client.post(
            "/api/v1/workout-logs/",
            headers=auth_headers,
            json={
                "title": "Lift",
                "workout_type": "strength",
                "duration_minutes": 30,
                "intensity": "moderate",
            },
        )

        assert cardio_response.json()["calories_burned"] > strength_response.json()["calories_burned"]


class TestWorkoutRetrieval:
    async def test_list_workouts(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        # Create workouts
        for title, wtype in [("Run", "cardio"), ("Lift", "strength"), ("Yoga", "yoga")]:
            await client.post(
                "/api/v1/workout-logs/",
                headers=auth_headers,
                json={
                    "title": title,
                    "workout_type": wtype,
                    "duration_minutes": 30,
                    "intensity": "moderate",
                },
            )

        response = await client.get("/api/v1/workout-logs/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 3

    async def test_delete_workout(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        create_response = await client.post(
            "/api/v1/workout-logs/",
            headers=auth_headers,
            json={
                "title": "Test Workout",
                "workout_type": "other",
                "duration_minutes": 20,
                "intensity": "low",
            },
        )
        log_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/api/v1/workout-logs/{log_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        get_response = await client.get(
            f"/api/v1/workout-logs/{log_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


class TestDashboard:
    async def test_get_dashboard(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        response = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert "summary" in data
        assert "food_logs" in data
        assert "workout_logs" in data
        assert "calorie_progress" in data
        assert "protein_progress" in data
