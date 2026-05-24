"""
Activity API — step logs.

POST /activity/steps   → upsert today's (or a given date's) step count
GET  /activity/steps   → last N days of step logs for the current user
"""
import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.step_log import StepLog
from app.models.user import User
from app.schemas.activity import StepHistoryResponse, StepLogCreate, StepLogResponse

router = APIRouter(prefix="/activity", tags=["activity"])


@router.post(
    "/steps",
    response_model=StepLogResponse,
    summary="Log today's steps (upsert)",
)
async def upsert_steps(
    body: StepLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StepLog:
    """
    Upsert the step count for a given date (defaults to today).
    Calling this again on the same date overwrites the previous value.
    """
    log_date = body.date or datetime.date.today()

    # Delete existing entry for that date if it exists
    await db.execute(
        delete(StepLog).where(
            StepLog.user_id == current_user.id,
            StepLog.date == log_date,
        )
    )

    step_log = StepLog(
        user_id=current_user.id,
        date=log_date,
        steps=body.steps,
    )
    db.add(step_log)
    await db.commit()
    await db.refresh(step_log)
    return step_log


@router.get(
    "/steps",
    response_model=StepHistoryResponse,
    summary="Get step history",
)
async def get_step_history(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StepHistoryResponse:
    """
    Return the last `days` days of step logs, newest first.
    Days with no logged steps are omitted.
    """
    since = datetime.date.today() - datetime.timedelta(days=days - 1)

    result = await db.execute(
        select(StepLog)
        .where(
            StepLog.user_id == current_user.id,
            StepLog.date >= since,
        )
        .order_by(StepLog.date.desc())
    )
    logs = list(result.scalars().all())

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
