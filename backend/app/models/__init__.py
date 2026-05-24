"""
ORM model imports.

Import all models here so Alembic can discover them during migrations.
The import order matters for foreign key resolution in some edge cases.
"""
from app.models.base import Base
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

__all__ = [
    "Base",
    "User",
    "UserPreference",
    "FoodLog",
    "WorkoutLog",
    "FoodMemory",
    "NutritionCache",
    "DailySummary",
    "CorrectionEvent",
    "ProgressCheckpoint",
    "ProgressPhoto",
    "StepLog",
    "DailyReport",
    "BehaviorEvent",
]
