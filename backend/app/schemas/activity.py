"""
Activity (step log) schemas.
"""
import datetime
from uuid import UUID

from app.schemas.common import TrackBaseSchema


class StepLogCreate(TrackBaseSchema):
    """Body for POST /api/v1/activity/steps."""
    steps: int
    date: datetime.date | None = None  # defaults to today if omitted


class StepLogResponse(TrackBaseSchema):
    """Single day's step log."""
    id: UUID
    date: datetime.date
    steps: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class StepHistoryResponse(TrackBaseSchema):
    """Last N days of step logs (sorted newest-first)."""
    items: list[StepLogResponse]
    total: int
