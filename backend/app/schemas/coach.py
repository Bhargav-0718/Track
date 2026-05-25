"""
Coach schemas — request/response types for the AI coach chat endpoint.
"""
from datetime import datetime

from app.schemas.common import TrackBaseSchema


class CoachChatRequest(TrackBaseSchema):
    """Body for POST /coach/chat."""
    message: str


class CoachMessageSchema(TrackBaseSchema):
    """A single message in the coach conversation (for history endpoint)."""
    role: str           # "user" | "assistant"
    content: str
    created_at: datetime


class CoachSessionSchema(TrackBaseSchema):
    """The user's coach session with recent messages."""
    messages: list[CoachMessageSchema]
