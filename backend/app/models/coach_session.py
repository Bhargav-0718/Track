"""
CoachSession — MongoDB document storing the AI coach conversation history.

One session per user (get_or_create pattern).
Messages are embedded documents, trimmed to MAX_STORED_MESSAGES.
The LLM only sees the most recent LLM_CONTEXT_MESSAGES for token efficiency.
"""
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from beanie import Indexed
from pydantic import BaseModel, Field

from app.models.base import BaseDocument

MAX_STORED_MESSAGES = 100   # kept in MongoDB per session
LLM_CONTEXT_MESSAGES = 20   # sent to LLM each turn (keeps tokens ~manageable)


class CoachMessage(BaseModel):
    """An individual turn in the coach conversation."""
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CoachSession(BaseDocument):
    """
    Persistent conversation session between a user and the AI coach.

    One active session per user — use CoachSession.for_user() to get/create.
    Messages are appended via add_message() which handles the trim automatically.
    """
    user_id: Annotated[UUID, Indexed(unique=True)]
    messages: list[CoachMessage] = Field(default_factory=list)

    class Settings:
        name = "coach_sessions"

    # ── Class methods ──────────────────────────────────────────────────────────

    @classmethod
    async def for_user(cls, user_id: UUID) -> "CoachSession":
        """Get the existing session for a user, or create a new one."""
        session = await cls.find_one(cls.user_id == user_id)
        if session is None:
            session = cls(user_id=user_id)
            await session.insert()
        return session

    # ── Instance helpers ───────────────────────────────────────────────────────

    def add_message(self, role: Literal["user", "assistant"], content: str) -> None:
        """Append a message and trim history to MAX_STORED_MESSAGES."""
        self.messages.append(CoachMessage(role=role, content=content))
        if len(self.messages) > MAX_STORED_MESSAGES:
            self.messages = self.messages[-MAX_STORED_MESSAGES:]

    def get_llm_history(self) -> list[dict]:
        """Return the last LLM_CONTEXT_MESSAGES formatted for the OpenAI API."""
        recent = self.messages[-LLM_CONTEXT_MESSAGES:]
        return [{"role": m.role, "content": m.content} for m in recent]
