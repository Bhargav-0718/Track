"""
AI Coach endpoints.

Routes:
  POST /coach/chat      → Stream a coach reply as SSE (text/event-stream)
  GET  /coach/history   → Return the last N messages for the current session
  DELETE /coach/history → Clear the conversation history
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, CurrentUserID
from app.models.coach_session import CoachSession
from app.schemas.coach import CoachChatRequest, CoachMessageSchema, CoachSessionSchema
from app.services.ai.coach_agent import run_coach

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post(
    "/chat",
    summary="Send a message to the AI fitness coach (SSE stream)",
)
async def coach_chat(
    body: CoachChatRequest,
    current_user: CurrentUser,
) -> StreamingResponse:
    """
    Send a message to the AI coach and receive a streaming reply.

    **Response format**: `text/event-stream` — each event is a JSON object:

    ```
    data: {"type": "text_delta",     "content": "Nice lunch!"}
    data: {"type": "food_logged",    "food_name": "Dal Chawal", "calories": 420, "meal_type": "lunch"}
    data: {"type": "workout_logged", "workout_type": "strength", "duration_minutes": 45, "calories_burned": 280}
    data: {"type": "steps_logged",   "steps": 8500}
    data: {"type": "error",          "message": "..."}
    data: {"type": "done"}
    ```

    The `text_delta` events stream the reply word-by-word.
    Action events (`food_logged`, etc.) are emitted AFTER the text stream completes,
    so the UI can refresh relevant data when it sees them.
    """
    # Load existing session history
    session = await CoachSession.for_user(current_user.id)
    history = session.get_llm_history()

    # Quick context values injected into the system prompt
    today_calories = 0.0
    try:
        from datetime import date
        from app.repositories.food_log_repository import FoodLogRepository
        totals = await FoodLogRepository().get_daily_nutrition_totals(
            current_user.id, date.today()
        )
        today_calories = totals["total_calories"]
    except Exception:
        pass

    generator = run_coach(
        user_id=current_user.id,
        user_message=body.message,
        history=history,
        user_name=current_user.display_name,
        goal=current_user.goal,
        target_calories=current_user.target_calories,
        today_calories=today_calories,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering for SSE
        },
    )


@router.get(
    "/history",
    response_model=CoachSessionSchema,
    summary="Get coach conversation history",
)
async def get_coach_history(
    current_user_id: CurrentUserID,
    limit: int = 40,
) -> CoachSessionSchema:
    """
    Return the last `limit` messages from the user's coach session.
    Used to hydrate the chat UI on page load.
    """
    session = await CoachSession.for_user(current_user_id)
    recent = session.messages[-limit:]
    return CoachSessionSchema(
        messages=[
            CoachMessageSchema(
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in recent
        ]
    )


@router.delete(
    "/history",
    status_code=204,
    summary="Clear coach conversation history",
)
async def clear_coach_history(
    current_user_id: CurrentUserID,
) -> None:
    """Clear all messages in the user's coach session (fresh start)."""
    session = await CoachSession.for_user(current_user_id)
    session.messages = []
    await session.save_with_ts()
