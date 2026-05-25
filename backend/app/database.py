"""
MongoDB database connection and Beanie ODM initialization.

Design decisions:
- Motor (async MongoDB driver) + Beanie (ODM on top of Motor)
- Single global client — initialized at startup, closed at shutdown
- Beanie handles document model registration
- No per-request sessions — Beanie documents operate globally
"""
from typing import TYPE_CHECKING

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

# ── Client Singleton ───────────────────────────────────────────────────────────

_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]


async def init_db() -> None:
    """
    Initialize the MongoDB connection and register all Beanie document models.
    Called once at application startup.
    """
    global _client

    # Import all document models for Beanie registration
    from app.models.behavior_event import BehaviorEvent
    from app.models.correction_event import CorrectionEvent
    from app.models.daily_report import DailyReport
    from app.models.daily_summary import DailySummary
    from app.models.food_log import FoodLog
    from app.models.food_memory import FoodMemory
    from app.models.nutrition_cache import NutritionCache
    from app.models.progress_checkpoint import ProgressCheckpoint
    from app.models.progress_photo import ProgressPhoto
    from app.models.step_log import StepLog
    from app.models.user import User
    from app.models.user_preference import UserPreference
    from app.models.workout_log import WorkoutLog
    from beanie import init_beanie

    _client = AsyncIOMotorClient(settings.mongodb_url)
    database = _client[settings.mongodb_db_name]

    await init_beanie(
        database=database,
        document_models=[
            User,
            UserPreference,
            FoodLog,
            WorkoutLog,
            FoodMemory,
            NutritionCache,
            DailySummary,
            CorrectionEvent,
            ProgressCheckpoint,
            ProgressPhoto,
            StepLog,
            DailyReport,
            BehaviorEvent,
        ],
    )


async def close_db() -> None:
    """Close the MongoDB connection. Called at application shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def check_database_connection() -> bool:
    """Verify the database is reachable. Used in health check endpoint."""
    try:
        probe_client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=3000,
        )
        await probe_client.server_info()
        probe_client.close()
        return True
    except Exception:
        return False
