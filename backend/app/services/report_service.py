"""
ReportService — orchestrates daily AI report generation.

Flow:
  1. Check if report already exists for the date (skip if not force_regenerate)
  2. Call AnalyticsService to compute all behavioral metrics
  3. Build ReportContext from metrics
  4. Call generate_daily_report() → AI narrative
  5. Upsert DailyReport into DB
  6. Return DailyReportResponse

This service is the single entry point for all report generation.
It separates the orchestration (ReportService) from the AI generation
(ai/report_service.py) so metrics computation and prompt building are testable
without making AI API calls.
"""
from datetime import date, datetime, timezone
from uuid import UUID

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.daily_report import DailyReport
from app.repositories.daily_report_repository import DailyReportRepository
from app.schemas.report import (
    DailyReportResponse,
    DailyReportSummary,
    ReportStyle,
)
from app.services.ai.report_service import ReportContext, generate_daily_report
from app.services.analytics_service import AnalyticsService

logger = get_logger(__name__)


class ReportService:
    def __init__(self) -> None:
        self.report_repo = DailyReportRepository()
        self.analytics = AnalyticsService()

    async def get_or_generate(
        self,
        user_id: UUID,
        report_date: date | None = None,
        report_style: ReportStyle | None = None,
        force_regenerate: bool = False,
    ) -> DailyReportResponse:
        """
        Get an existing report or generate a new one for the given date.
        Idempotent — calling twice returns the same report unless force_regenerate=True.
        """
        target_date = report_date or date.today()

        # Return cached report if it exists (and force_regenerate is False)
        if not force_regenerate:
            existing = await self.report_repo.get_for_date(user_id, target_date)
            if existing:
                logger.info(
                    "report_cache_hit",
                    user_id=str(user_id),
                    date=str(target_date),
                )
                return self._to_response(existing)

        # Compute all behavioral metrics
        logger.info(
            "report_generation_triggered",
            user_id=str(user_id),
            date=str(target_date),
            force=force_regenerate,
        )
        metrics = await self.analytics.compute_report_context_metrics(user_id, target_date)

        # Resolve report style: request override → user preference → default
        style = report_style or "motivational"  # Future: load from user.preference

        # Build ReportContext
        ctx = ReportContext(
            report_date=target_date,
            report_style=style,  # type: ignore[arg-type]
            goal=metrics["goal"],
            target_calories=metrics["target_calories"],
            target_protein_g=metrics["target_protein_g"],
            actual_calories=metrics["actual_calories"],
            actual_protein_g=metrics["actual_protein_g"],
            actual_carbs_g=metrics["actual_carbs_g"],
            actual_fat_g=metrics["actual_fat_g"],
            meals_logged=metrics["meals_logged"],
            workouts_completed=metrics["workouts_completed"],
            total_calories_burned=metrics["total_calories_burned"],
            workout_types=metrics["workout_types"],
            workout_duration_minutes=metrics["workout_duration_minutes"],
            streak_days=metrics["streak_days"],
            consistency_7d=metrics["consistency_7d"],
            calorie_adherence_7d=metrics["calorie_adherence_7d"],
            protein_adherence_7d=metrics["protein_adherence_7d"],
            correction_rate_pct=metrics["correction_rate_pct"],
            behavioral_patterns=metrics["behavioral_patterns"],
        )

        # Generate AI narrative
        ai_output = await generate_daily_report(ctx)

        # Build summary dicts for DB storage
        calorie_summary = {
            "target": metrics["target_calories"],
            "actual": metrics["actual_calories"],
            "adherence_pct": round(
                (metrics["actual_calories"] / metrics["target_calories"] * 100)
                if metrics["target_calories"]
                else 0,
                1,
            ),
            "deficit_or_surplus": round(
                metrics["actual_calories"] - (metrics["target_calories"] or 0), 1
            ),
        }

        workout_summary = {
            "count": metrics["workouts_completed"],
            "calories_burned": metrics["total_calories_burned"],
            "net_calories": round(
                metrics["actual_calories"] - metrics["total_calories_burned"], 1
            ),
            "types": metrics["workout_types"],
            "duration_minutes": metrics["workout_duration_minutes"],
            "rest_day": metrics["workouts_completed"] == 0,
        }

        macro_summary = {
            "protein_g": metrics["actual_protein_g"],
            "protein_target_g": metrics["target_protein_g"],
            "carbs_g": metrics["actual_carbs_g"],
            "fat_g": metrics["actual_fat_g"],
        }

        consistency_score = metrics["consistency_7d"]  # 0.0–1.0

        # Upsert report in DB
        report = await self.report_repo.upsert(
            user_id=user_id,
            report_date=target_date,
            calorie_summary=calorie_summary,
            workout_summary=workout_summary,
            macro_summary=macro_summary,
            consistency_score=consistency_score,
            streak_days=metrics["streak_days"],
            weekly_consistency=metrics["consistency_7d"],
            insights_text=ai_output.insights_text,
            motivation_message=ai_output.motivation_message,
            behavioral_observations=ai_output.behavioral_observations,
            report_style=style,
        )

        return self._to_response(report)

    async def get_report(
        self,
        user_id: UUID,
        report_date: date,
    ) -> DailyReportResponse:
        """Fetch an existing report. Does NOT generate if missing."""
        report = await self.report_repo.get_for_date(user_id, report_date)
        if not report:
            raise ResourceNotFoundError(
                message=f"No report found for {report_date}. Use POST /reports/generate to create one.",
                resource_type="DailyReport",
                resource_id=str(report_date),
            )
        return self._to_response(report)

    async def list_reports(
        self,
        user_id: UUID,
        limit: int = 30,
        offset: int = 0,
    ) -> list[DailyReportSummary]:
        reports = await self.report_repo.list_for_user(user_id, limit=limit, offset=offset)
        return [
            DailyReportSummary(
                id=r.id,
                report_date=r.report_date,
                consistency_score=r.consistency_score,
                streak_days=r.streak_days,
                insights_text=(r.insights_text or "")[:200] if r.insights_text else None,
                was_shown=r.was_shown,
                user_rating=r.user_rating,
                created_at=r.created_at,
            )
            for r in reports
        ]

    async def mark_shown(self, user_id: UUID, report_id: UUID) -> DailyReportResponse:
        """Mark a report as viewed (called when Flutter opens the report card)."""
        report = await self._get_report_for_user(user_id, report_id)
        report = await self.report_repo.mark_shown(report)
        return self._to_response(report)

    async def rate_report(
        self,
        user_id: UUID,
        report_id: UUID,
        rating: int,
    ) -> DailyReportResponse:
        """Store user rating. Ratings 1-5 feed future style preference learning."""
        if not 1 <= rating <= 5:
            raise ValidationError(message="Rating must be between 1 and 5")

        report = await self._get_report_for_user(user_id, report_id)
        report = await self.report_repo.set_rating(report, rating)

        # Record engagement event
        await self.report_repo.record_event(
            user_id=user_id,
            event_type="report_rated",
            entity_id=report_id,
            entity_type="daily_report",
            metadata={"rating": rating, "report_style": report.report_style},
        )

        logger.info(
            "report_rated",
            report_id=str(report_id),
            rating=rating,
            style=report.report_style,
        )
        return self._to_response(report)

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_report_for_user(self, user_id: UUID, report_id: UUID) -> DailyReport:
        """Fetch a report document, verifying ownership."""
        report = await DailyReport.find_one(
            DailyReport.id == report_id,
            DailyReport.user_id == user_id,
        )
        if not report:
            raise ResourceNotFoundError(
                message=f"Report {report_id} not found",
                resource_type="DailyReport",
                resource_id=str(report_id),
            )
        return report

    def _to_response(self, report: DailyReport) -> DailyReportResponse:
        return DailyReportResponse(
            id=report.id,
            report_date=report.report_date,
            calorie_summary=report.calorie_summary,
            workout_summary=report.workout_summary,
            macro_summary=report.macro_summary,
            consistency_score=report.consistency_score,
            streak_days=report.streak_days,
            weekly_consistency=report.weekly_consistency,
            insights_text=report.insights_text,
            motivation_message=report.motivation_message,
            behavioral_observations=report.behavioral_observations,
            report_style=report.report_style,  # type: ignore[arg-type]
            generation_model=report.generation_model,
            was_shown=report.was_shown,
            shown_at=report.shown_at,
            user_rating=report.user_rating,
            created_at=report.created_at,
        )
