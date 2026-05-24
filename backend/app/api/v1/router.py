"""
v1 API router — aggregates all route modules.
"""
from fastapi import APIRouter

from app.api.v1 import analytics, checkpoints, food_logs, reports, users, workout_logs

api_router = APIRouter()

# Auth + Users
api_router.include_router(users.router)

# Food Logs (Phase 1 + 2)
api_router.include_router(food_logs.router)

# Workout Logs + Dashboard + Health Connect (Phase 1)
api_router.include_router(workout_logs.router)

# Progress Checkpoints + Photo Upload + AI Comparison (Phase 3)
api_router.include_router(checkpoints.router)

# Daily AI Reports (Phase 4)
api_router.include_router(reports.router)

# Behavioral Analytics (Phase 4)
api_router.include_router(analytics.router)
