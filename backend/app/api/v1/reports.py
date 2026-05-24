"""
Daily AI report endpoints.

Routes:
  POST   /reports/generate          → Generate (or get) report for a date
  GET    /reports/                  → List report history
  GET    /reports/{date}            → Get report for a specific date
  POST   /reports/{id}/shown        → Mark report as viewed
  POST   /reports/{id}/rate         → Rate a report (1-5)
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUserID, DbSession
from app.schemas.report import (
    DailyReportResponse,
    DailyReportSummary,
    ReportGenerateRequest,
    ReportRateRequest,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_model=DailyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate or retrieve a daily AI report",
)
async def generate_report(
    data: ReportGenerateRequest,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> DailyReportResponse:
    """
    Generate an AI-powered daily report.

    If a report already exists for the requested date and `force_regenerate`
    is False (default), the cached report is returned immediately — no AI call.

    **What's included**:
    - Calorie and macro summary vs your targets
    - Workout summary and net calorie balance
    - 7-day consistency metrics and logging streak
    - AI-generated narrative insights (style adapts to your preference)
    - Personalized motivational message
    - Behavioral pattern observations

    **Report styles**:
    - `motivational`: High-energy, celebrate wins, positive reframes
    - `analytical`: Data-focused, precise, trend-based
    - `brief`: Concise bullets, fast to read
    - `detailed`: Comprehensive analysis with context

    Defaults to your saved preference (set in user preferences).
    The first call of the day triggers an AI API call (~2-4 seconds).
    """
    service = ReportService(db)
    return await service.get_or_generate(
        user_id=current_user_id,
        report_date=data.report_date,
        report_style=data.report_style,
        force_regenerate=data.force_regenerate,
    )


@router.get(
    "/",
    response_model=list[DailyReportSummary],
    summary="List report history",
)
async def list_reports(
    current_user_id: CurrentUserID,
    db: DbSession,
    limit: int = 30,
    offset: int = 0,
) -> list[DailyReportSummary]:
    """
    List past daily reports, newest first.
    Returns lightweight summaries — use GET /reports/{date} for full content.
    """
    service = ReportService(db)
    return await service.list_reports(current_user_id, limit=limit, offset=offset)


@router.get(
    "/{report_date}",
    response_model=DailyReportResponse,
    summary="Get report for a specific date",
)
async def get_report(
    report_date: date,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> DailyReportResponse:
    """
    Get the full report for a specific date (YYYY-MM-DD).
    Returns 404 if no report has been generated for that date yet.
    Use POST /reports/generate to create one.
    """
    service = ReportService(db)
    return await service.get_report(current_user_id, report_date)


@router.post(
    "/{report_id}/shown",
    response_model=DailyReportResponse,
    summary="Mark report as viewed",
)
async def mark_report_shown(
    report_id: UUID,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> DailyReportResponse:
    """
    Mark a report as viewed. Call this when the Flutter UI displays the report card.
    Records `shown_at` timestamp for engagement analytics.
    """
    service = ReportService(db)
    return await service.mark_shown(current_user_id, report_id)


@router.post(
    "/{report_id}/rate",
    response_model=DailyReportResponse,
    summary="Rate a report",
)
async def rate_report(
    report_id: UUID,
    data: ReportRateRequest,
    current_user_id: CurrentUserID,
    db: DbSession,
) -> DailyReportResponse:
    """
    Rate a daily report from 1-5.

    Ratings are used to learn your preferred report style over time.
    A 5-star rating means the style/content worked well for you today.
    Low ratings indicate the style should be adjusted.
    """
    service = ReportService(db)
    return await service.rate_report(current_user_id, report_id, data.rating)
