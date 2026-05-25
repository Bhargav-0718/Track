"""
Activity API — step logs.

POST /activity/steps   → upsert today's (or a given date's) step count
GET  /activity/steps   → last N days of step logs for the current user
"""
import datetime

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.models.step_log import StepLog
from app.schemas.activity import StepHistoryResponse, StepLogCreate, StepLogResponse

router = APIRouter(prefix="/activity", tags=["activity"])


@router.post(
    "/steps",
    response_model=StepLogResponse,
    summary="Log today's steps (upsert)",
)
async def upsert_steps(
    body: StepLogCreate,
    current_user: CurrentUser,
) -> StepLogResponse:
    """
    Upsert the step count for a given date (defaults to today).
    Calling this again on the same date overwrites the previous value.
    """
    log_date = body.date or datetime.date.today()

    # Delete existing entry for that date if it exists (upsert pattern)
    existing = await StepLog.find_one(
        StepLog.user_id == current_user.id,
        StepLog.date == log_date,
    )
    if existing:
        await existing.delete()

    step_log = StepLog(
        user_id=current_user.id,
        date=log_date,
        steps=body.steps,
    )
    await step_log.insert()

    return StepLogResponse(
        id=step_log.id,
        date=step_log.date,
        steps=step_log.steps,
        created_at=step_log.created_at,
        updated_at=step_log.updated_at,
    )


@router.get(
    "/steps",
    response_model=StepHistoryResponse,
    summary="Get step history",
)
async def get_step_history(
    current_user: CurrentUser,
    days: int = Query(default=7, ge=1, le=90),
) -> StepHistoryResponse:
    """
    Return the last `days` days of step logs, newest first.
    Days with no logged steps are omitted.
    """
    since = datetime.date.today() - datetime.timedelta(days=days - 1)

    logs = await StepLog.find(
        StepLog.user_id == current_user.id,
        StepLog.date >= since,
    ).to_list()

    logs.sort(key=lambda l: l.date, reverse=True)

    return StepHistoryResponse(
        items=[
            StepLogResponse(
                id=log.id,
                date=log.date,
                steps=log.steps,
                created_at=log.created_at,
                updated_at=log.updated_at,
            )
            for log in logs
        ],
        total=len(logs),
    )
