"""
CoachAgent — AI fitness coach with tool use, persona, and SSE streaming.

Architecture:
  1. User message arrives with session history
  2. Build messages: system prompt (with live context) + history + new message
  3. Agent loop (non-streaming):
       a. Call GPT-4o-mini with tools
       b. If tool_calls: execute them, append results, loop again
       c. If no tool_calls: break — this is the final response
  4. Stream the final response as SSE text_delta events
  5. Save assistant reply + any action events to session

Tools the coach has:
  get_today_context     → today's calories, meals, workouts, steps
  get_weekly_summary    → 7-day trend overview
  estimate_food         → estimate nutrition (no DB write)
  log_food              → commit food log to DB (only after user confirms)
  log_workout           → commit workout log to DB (only after user confirms)
  log_steps             → commit step count to DB (only after user confirms)

SSE event types (yielded as "data: <json>\\n\\n"):
  {"type": "text_delta",      "content": "..."}
  {"type": "food_logged",     "food_name": "...", "calories": 380}
  {"type": "workout_logged",  "workout_type": "strength", "duration_minutes": 45}
  {"type": "steps_logged",    "steps": 8000}
  {"type": "done"}
  {"type": "error",           "message": "..."}
"""
import json
from datetime import date, datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

from app.core.logging import get_logger
from app.models.step_log import StepLog
from app.services.ai.client import get_openai_client

logger = get_logger(__name__)

COACH_MODEL = "gpt-4o-mini"
MAX_TOOL_LOOPS = 6   # safety cap — prevents infinite tool loops


# ── Persona & System Prompt ────────────────────────────────────────────────────

_BASE_SYSTEM_PROMPT = """
You are Vajra — a fitness coach inside the Track app. Vajra means thunderbolt. \
Sharp, direct, no fluff.

════ WHO YOU ARE ════

You talk like a real person who knows fitness — not a customer service bot.
You know Indian food natively: roti, dal, sabji, chaas, poha, idli, biryani, \
khichdi, rajma, chole — you never ask "what is that?" or "can you clarify?".
You are brief. You are direct. You have opinions.

════ HOW YOU SOUND — READ THIS CAREFULLY ════

WRONG (chatbot):         RIGHT (Vajra):
──────────────────────   ──────────────────────────────────────────
"Great job!"             "Solid." / "Not bad." / "That's the way."
"Awesome work!"          [say nothing or say what was actually good]
"Let me estimate that    [just call the tool, then give the result]
 for you! Just a moment"
"Does that sound good?"  "Log it?"
"Want me to log those    "8000 steps — log it?"
 8000 steps for you?"
"Let's break that down:" "Treadmill 10 + cycle 7 + cardio 8 = 25 mins."
Bullet lists for         Write inline: "10 min treadmill, 7 min cycle,
simple workout info       8 min cardio — 25 mins total."

════ FORMATTING RULES ════

- Write like you're texting. No bullet lists for simple things.
- Numbers inline: "2 roti + 1 bowl dahi = ~380 kcal" not a bulleted list.
- Bold only the total or key number, not sub-headers.
- Max 3-4 lines for most replies. If it fits in one line, use one line.
- No em-dashes as bullet replacements. No "Here's what I found:".

════ YOUR JOB ════

1. Log food → ALWAYS call estimate_food first, show the total, ask "Log it?"
2. Log workouts → ask once to confirm, then call log_workout.
3. Log steps → confirm once, log it.
4. Answer questions → call get_today_context or get_weekly_summary for real data.

For WORKOUT CALORIES specifically:
- Do NOT invent calorie numbers out of thin air.
- Say: "Exact burn gets calculated when I log it — roughly X kcal for Y mins \
  of [type]." Use these rough ranges: cardio ~6-8 kcal/min, strength ~4-5 \
  kcal/min, HIIT ~9-11 kcal/min, yoga ~3-4 kcal/min.
- Then ask to log it.

════ HARD RULES ════

- NEVER say: "As an AI", "Great job!", "Awesome!", "Of course!", "Certainly!",
  "Let me", "Just a moment", "Does that sound good?", "I'd be happy to".
- NEVER make up exact calorie numbers — use ranges or call the tool.
- NEVER log anything without the user saying yes/confirm/log it/haan/sure/ha.
- NEVER ask for confirmation twice for the same thing.
- ONE nudge max on health topics — mention it once, then drop it.
- NEVER give medical advice.

════ PERSONALITY EXTRAS ════

- Notice things the user doesn't mention: "8000 steps plus 25 min cardio — \
  good active day."
- Give real opinions occasionally: "7 min cycle is short — worth bumping to 15 \
  next time."
- Use the user's name sometimes, not every message.
- Light Hinglish is fine if the user uses it: "haan", "kal", "bhai".
""".strip()


def _build_system_prompt(
    user_name: str,
    goal: str,
    target_calories: float | None,
    today_calories: float,
    current_time: str,
) -> str:
    """Inject live user context into the system prompt."""
    goal_label = {
        "lose_weight": "lose weight",
        "maintain": "maintain weight",
        "gain_muscle": "gain muscle",
        "improve_fitness": "improve fitness",
    }.get(goal, goal)

    cal_status = (
        f"{today_calories:.0f} / {target_calories:.0f} kcal eaten today"
        if target_calories
        else f"{today_calories:.0f} kcal eaten today"
    )

    context = f"""
CURRENT SESSION CONTEXT (do not repeat this to the user verbatim):
- User's name: {user_name}
- Goal: {goal_label}
- Time now: {current_time}
- Calories today: {cal_status}
""".strip()

    return f"{_BASE_SYSTEM_PROMPT}\n\n{context}"


# ── Tool Definitions ───────────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_today_context",
            "description": (
                "Get the user's full activity for today: all food logged (with calories), "
                "workouts, steps, and totals vs targets. "
                "Call this at the start of a conversation or whenever you need current data."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weekly_summary",
            "description": (
                "Get a 7-day nutrition and activity trend: daily calorie averages, "
                "workout frequency, step averages, and consistency. "
                "Call when the user asks about their week, trends, or progress."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_food",
            "description": (
                "Estimate calories and macros for a food description. "
                "Returns a detailed per-item breakdown. "
                "ALWAYS call this before log_food — never guess calories yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": (
                            "Natural language food description. "
                            "E.g. '2 roti + 1 katori dahi + soyabean sabji'"
                        ),
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": [
                            "breakfast", "lunch", "dinner",
                            "snack", "pre_workout", "post_workout",
                        ],
                        "description": "Infer from time of day and conversation context.",
                    },
                },
                "required": ["description", "meal_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_food",
            "description": (
                "Commit a food entry to the user's food diary. "
                "Only call this AFTER showing the estimate AND receiving explicit "
                "user confirmation ('yes', 'log it', 'confirm', 'haan', 'sure', 'okay')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "The food description (same string used in estimate_food).",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": [
                            "breakfast", "lunch", "dinner",
                            "snack", "pre_workout", "post_workout",
                        ],
                    },
                },
                "required": ["description", "meal_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_workout",
            "description": (
                "Commit a workout session to the user's log. "
                "Only call after the user explicitly confirms."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_type": {
                        "type": "string",
                        "enum": ["strength", "cardio", "hiit", "yoga", "sports", "other"],
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration in minutes.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional short note e.g. 'chest + shoulders', 'morning run'.",
                    },
                },
                "required": ["workout_type", "duration_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_steps",
            "description": (
                "Log the user's step count for today. "
                "Only call after the user explicitly confirms."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "integer",
                        "description": "Number of steps to log for today.",
                    },
                },
                "required": ["steps"],
            },
        },
    },
]


# ── Tool Executors ─────────────────────────────────────────────────────────────

async def _exec_get_today_context(user_id: UUID) -> dict:
    """Fetch today's food, workout, and step summary from the DB."""
    from datetime import date as date_type
    from app.repositories.food_log_repository import FoodLogRepository
    from app.repositories.workout_log_repository import WorkoutLogRepository
    from app.models.user import User

    today = date_type.today()
    food_repo = FoodLogRepository()
    workout_repo = WorkoutLogRepository()

    # Food
    food_totals = await food_repo.get_daily_nutrition_totals(user_id, today)
    food_logs = await food_repo.get_logs_for_date(user_id, today)

    # Workouts
    workouts = await workout_repo.get_logs_for_date(user_id, today)

    # Steps
    step_log = await StepLog.find_one({"user_id": user_id, "date": today})

    # User targets
    user = await User.find_one(User.id == user_id)
    target_cal = user.target_calories if user else None
    target_protein = user.target_protein_g if user else None
    step_target = user.daily_steps_target if user else 10000

    meals_summary = []
    for log in food_logs:
        meals_summary.append({
            "food": log.food_name,
            "meal_type": log.meal_type,
            "calories": round(log.calories),
            "protein_g": round(log.protein_g or 0),
        })

    workouts_summary = []
    for w in workouts:
        workouts_summary.append({
            "type": w.workout_type,
            "duration_min": w.duration_minutes,
            "calories_burned": round(w.calories_burned or 0),
        })

    return {
        "date": today.isoformat(),
        "nutrition": {
            "total_calories": round(food_totals["total_calories"]),
            "total_protein_g": round(food_totals["total_protein"]),
            "total_carbs_g": round(food_totals["total_carbs"]),
            "total_fat_g": round(food_totals["total_fat"]),
            "target_calories": round(target_cal) if target_cal else None,
            "target_protein_g": round(target_protein) if target_protein else None,
            "meals_logged": food_totals["count"],
        },
        "meals": meals_summary,
        "workouts": workouts_summary,
        "steps": {
            "count": step_log.steps if step_log else 0,
            "target": step_target,
        },
    }


async def _exec_get_weekly_summary(user_id: UUID) -> dict:
    """Fetch 7-day nutrition and activity averages."""
    from datetime import date as date_type, timedelta
    from app.repositories.food_log_repository import FoodLogRepository
    from app.repositories.workout_log_repository import WorkoutLogRepository

    today = date_type.today()
    food_repo = FoodLogRepository()
    workout_repo = WorkoutLogRepository()

    days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        totals = await food_repo.get_daily_nutrition_totals(user_id, d)
        days.append({
            "date": d.isoformat(),
            "calories": round(totals["total_calories"]),
            "protein_g": round(totals["total_protein"]),
            "meals_logged": totals["count"],
        })

    total_calories = sum(d["calories"] for d in days)
    days_with_data = sum(1 for d in days if d["meals_logged"] > 0)
    avg_calories = round(total_calories / max(days_with_data, 1))

    step_logs = await StepLog.find(
        {"user_id": user_id, "date": {"$gte": today - timedelta(days=6)}}
    ).to_list()
    avg_steps = round(sum(s.steps for s in step_logs) / max(len(step_logs), 1))

    return {
        "days": days,
        "summary": {
            "days_logged": days_with_data,
            "avg_daily_calories": avg_calories,
            "avg_steps": avg_steps,
            "consistency_pct": round((days_with_data / 7) * 100),
        },
    }


async def _exec_estimate_food(description: str, meal_type: str, user_id: UUID) -> dict:
    """Run the full estimation pipeline and return a breakdown (no DB write)."""
    from app.services.estimation_service import EstimationService

    estimator = EstimationService()
    result = await estimator.estimate(raw_input=description, user_id=user_id)

    return {
        "food_name": result.food_name,
        "description": description,
        "meal_type": meal_type,
        "calories": round(result.calories),
        "protein_g": round(result.protein_g or 0),
        "carbs_g": round(result.carbs_g or 0),
        "fat_g": round(result.fat_g or 0),
        "portion": result.portion_description,
        "confidence": result.confidence_level,
        "assumptions": result.assumptions,
        "estimation_source": result.estimation_source,
    }


async def _exec_log_food(
    description: str,
    meal_type: str,
    user_id: UUID,
) -> tuple[dict, dict]:
    """Write a food log via FoodService. Returns (tool_result, sse_event)."""
    from app.schemas.food_log import FoodLogCreate
    from app.schemas.common import MealType
    from app.services.food_service import FoodService

    data = FoodLogCreate(
        raw_input=description,
        meal_type=MealType(meal_type),
    )
    service = FoodService()
    log = await service.create_log(user_id, data)

    tool_result = {
        "logged": True,
        "food_name": log.food_name,
        "calories": round(log.calories),
        "meal_type": log.meal_type,
    }
    sse_event = {
        "type": "food_logged",
        "food_name": log.food_name,
        "calories": round(log.calories),
        "meal_type": log.meal_type,
    }
    return tool_result, sse_event


async def _exec_log_workout(
    workout_type: str,
    duration_minutes: int,
    user_id: UUID,
    notes: str | None = None,
) -> tuple[dict, dict]:
    """Write a workout log via WorkoutService. Returns (tool_result, sse_event)."""
    from app.schemas.workout_log import WorkoutLogCreate
    from app.services.workout_service import WorkoutService

    # Generate a friendly title from workout type
    type_label = {
        "strength": "Strength Training",
        "cardio": "Cardio Session",
        "hiit": "HIIT Workout",
        "yoga": "Yoga Session",
        "sports": "Sports Activity",
        "other": "Workout",
    }.get(workout_type, "Workout")

    data = WorkoutLogCreate(
        title=type_label,
        workout_type=workout_type,
        duration_minutes=duration_minutes,
        notes=notes,
        intensity="moderate",  # default — coach can refine later
    )
    service = WorkoutService()
    log = await service.create_log(user_id, data)

    tool_result = {
        "logged": True,
        "workout_type": log.workout_type,
        "duration_minutes": log.duration_minutes,
        "calories_burned": round(log.calories_burned or 0),
    }
    sse_event = {
        "type": "workout_logged",
        "workout_type": log.workout_type,
        "duration_minutes": log.duration_minutes,
        "calories_burned": round(log.calories_burned or 0),
    }
    return tool_result, sse_event


async def _exec_log_steps(steps: int, user_id: UUID) -> tuple[dict, dict]:
    """Upsert today's step count. Returns (tool_result, sse_event)."""
    import datetime as dt

    today = dt.date.today()
    existing = await StepLog.find_one({"user_id": user_id, "date": today})
    if existing:
        await existing.delete()

    step_log = StepLog(user_id=user_id, date=today, steps=steps)
    await step_log.insert()

    tool_result = {"logged": True, "steps": steps, "date": today.isoformat()}
    sse_event = {"type": "steps_logged", "steps": steps}
    return tool_result, sse_event


# ── Tool Dispatcher ────────────────────────────────────────────────────────────

async def _dispatch_tool(
    name: str,
    arguments: dict,
    user_id: UUID,
) -> tuple[dict, dict | None]:
    """
    Execute a tool call and return (result_for_llm, sse_event_or_None).

    sse_event is non-None only for mutating tools (log_*).
    """
    logger.info("coach_tool_call", tool=name, args=arguments)

    if name == "get_today_context":
        result = await _exec_get_today_context(user_id)
        return result, None

    if name == "get_weekly_summary":
        result = await _exec_get_weekly_summary(user_id)
        return result, None

    if name == "estimate_food":
        result = await _exec_estimate_food(
            description=arguments["description"],
            meal_type=arguments["meal_type"],
            user_id=user_id,
        )
        return result, None

    if name == "log_food":
        return await _exec_log_food(
            description=arguments["description"],
            meal_type=arguments["meal_type"],
            user_id=user_id,
        )

    if name == "log_workout":
        return await _exec_log_workout(
            workout_type=arguments["workout_type"],
            duration_minutes=arguments["duration_minutes"],
            user_id=user_id,
            notes=arguments.get("notes"),
        )

    if name == "log_steps":
        return await _exec_log_steps(
            steps=arguments["steps"],
            user_id=user_id,
        )

    return {"error": f"Unknown tool: {name}"}, None


# ── Main Agent Stream ──────────────────────────────────────────────────────────

async def run_coach(
    user_id: UUID,
    user_message: str,
    history: list[dict],
    user_name: str = "there",
    goal: str = "maintain",
    target_calories: float | None = None,
    today_calories: float = 0.0,
) -> AsyncGenerator[str, None]:
    """
    Run one turn of the AI coach conversation.

    Yields SSE-formatted strings ("data: <json>\\n\\n").
    Saves the assistant reply + action events internally.

    Args:
        user_id:         Authenticated user's UUID
        user_message:    The new message from the user
        history:         Previous messages [{role, content}, ...]
        user_name:       User's display name for personalisation
        goal:            User's fitness goal string
        target_calories: Daily calorie target (or None)
        today_calories:  Calories already logged today (for context)
    """
    now_str = datetime.now(timezone.utc).strftime("%A, %b %d %Y · %I:%M %p UTC")
    system_prompt = _build_system_prompt(
        user_name=user_name,
        goal=goal,
        target_calories=target_calories,
        today_calories=today_calories,
        current_time=now_str,
    )

    # Build full message list for LLM
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    client = get_openai_client()
    sse_events: list[dict] = []   # collected from tool executions
    full_assistant_text = ""      # collected for session persistence

    try:
        # ── Agent loop: execute tools until the model produces a final reply ──
        for loop_idx in range(MAX_TOOL_LOOPS):
            response = await client.chat.completions.create(
                model=COACH_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.85,
                max_tokens=500,
            )

            msg = response.choices[0].message
            tool_calls = msg.tool_calls or []

            if not tool_calls:
                # No tool calls — final text reply. Stream it.
                break

            # Append assistant turn (with tool_calls) to messages
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # Execute each tool and append results
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                    result, event = await _dispatch_tool(tc.function.name, args, user_id)
                except Exception as exc:
                    logger.error(
                        "coach_tool_error",
                        tool=tc.function.name,
                        error=str(exc),
                    )
                    result = {"error": str(exc)}
                    event = None

                if event:
                    sse_events.append(event)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        # ── Stream the final text response ────────────────────────────────────
        stream = await client.chat.completions.create(
            model=COACH_MODEL,
            messages=messages,
            stream=True,
            temperature=0.85,
            max_tokens=500,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_assistant_text += delta
                yield f"data: {json.dumps({'type': 'text_delta', 'content': delta})}\n\n"

        # ── Emit action events (food_logged, workout_logged, etc.) ────────────
        for event in sse_events:
            yield f"data: {json.dumps(event)}\n\n"

        # ── Persist both turns to the session ─────────────────────────────────
        from app.models.coach_session import CoachSession
        session = await CoachSession.for_user(user_id)
        session.add_message("user", user_message)
        session.add_message("assistant", full_assistant_text)
        await session.save_with_ts()

        logger.info(
            "coach_turn_complete",
            user_id=str(user_id),
            tool_loops=loop_idx + 1,
            action_events=len(sse_events),
            reply_len=len(full_assistant_text),
        )

    except Exception as exc:
        logger.error("coach_agent_error", error=str(exc))
        yield f"data: {json.dumps({'type': 'error', 'message': 'Something went wrong. Try again!'})}\n\n"

    finally:
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
