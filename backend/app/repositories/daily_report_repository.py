"""
DailyReportRepository — data access for daily reports and behavior events.
"""
from datetime import date, datetime
from datetime import timezone as dt_timezone
from uuid import UUID

from app.models.behavior_event import BehaviorEvent
from app.models.daily_report import DailyReport


class DailyReportRepository:
    # ── DailyReport ────────────────────────────────────────────────────────────

    async def get_for_date(
        self,
        user_id: UUID,
        report_date: date,
    ) -> DailyReport | None:
        return await DailyReport.find_one(
            DailyReport.user_id == user_id,
            DailyReport.report_date == report_date,
        )

    async def upsert(
        self,
        user_id: UUID,
        report_date: date,
        *,
        calorie_summary: dict,
        workout_summary: dict,
        macro_summary: dict,
        consistency_score: float,
        streak_days: int,
        weekly_consistency: float,
        insights_text: str | None = None,
        motivation_message: str | None = None,
        behavioral_observations: list[str] | None = None,
        report_style: str = "motivational",
        generation_model: str = "gpt-4o-mini",
    ) -> DailyReport:
        """Insert or update (overwrite) a daily report for the given date."""
        existing = await self.get_for_date(user_id, report_date)

        if existing:
            existing.calorie_summary = calorie_summary
            existing.workout_summary = workout_summary
            existing.macro_summary = macro_summary
            existing.consistency_score = consistency_score
            existing.streak_days = streak_days
            existing.weekly_consistency = weekly_consistency
            existing.insights_text = insights_text
            existing.motivation_message = motivation_message
            existing.behavioral_observations = behavioral_observations or []
            existing.report_style = report_style
            existing.generation_model = generation_model
            existing.updated_at = datetime.now(dt_timezone.utc)
            await existing.save()
            return existing
        else:
            report = DailyReport(
                user_id=user_id,
                report_date=report_date,
                calorie_summary=calorie_summary,
                workout_summary=workout_summary,
                macro_summary=macro_summary,
                consistency_score=consistency_score,
                streak_days=streak_days,
                weekly_consistency=weekly_consistency,
                insights_text=insights_text,
                motivation_message=motivation_message,
                behavioral_observations=behavioral_observations or [],
                report_style=report_style,
                generation_model=generation_model,
            )
            await report.insert()
            return report

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 30,
        offset: int = 0,
    ) -> list[DailyReport]:
        """Get report history, newest first."""
        reports = await DailyReport.find(
            DailyReport.user_id == user_id,
        ).sort(-DailyReport.report_date).skip(offset).limit(limit).to_list()
        return reports

    async def mark_shown(self, report: DailyReport) -> DailyReport:
        """Mark a report as viewed."""
        report.was_shown = True
        report.shown_at = datetime.now(dt_timezone.utc)
        report.updated_at = datetime.now(dt_timezone.utc)
        await report.save()
        return report

    async def set_rating(self, report: DailyReport, rating: int) -> DailyReport:
        """Store user's rating (1-5)."""
        report.user_rating = rating
        report.updated_at = datetime.now(dt_timezone.utc)
        await report.save()
        return report

    # ── BehaviorEvent ──────────────────────────────────────────────────────────

    async def record_event(
        self,
        user_id: UUID,
        event_type: str,
        entity_id: UUID | None = None,
        entity_type: str | None = None,
        metadata: dict | None = None,
    ) -> BehaviorEvent:
        event = BehaviorEvent(
            user_id=user_id,
            event_type=event_type,
            entity_id=entity_id,
            entity_type=entity_type,
            metadata_=metadata or {},
        )
        await event.insert()
        return event
