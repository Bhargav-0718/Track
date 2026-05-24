"""
DailyReportRepository — data access for daily reports and behavior events.
"""
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavior_event import BehaviorEvent
from app.models.daily_report import DailyReport


class DailyReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── DailyReport ────────────────────────────────────────────────────────────

    async def get_for_date(
        self,
        user_id: UUID,
        report_date: date,
    ) -> DailyReport | None:
        stmt = select(DailyReport).where(
            and_(
                DailyReport.user_id == user_id,
                DailyReport.report_date == report_date,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
        """
        Insert or update (overwrite) a daily report for the given date.
        Uses PostgreSQL ON CONFLICT DO UPDATE.
        """
        values = {
            "user_id": user_id,
            "report_date": report_date,
            "calorie_summary": calorie_summary,
            "workout_summary": workout_summary,
            "macro_summary": macro_summary,
            "consistency_score": consistency_score,
            "streak_days": streak_days,
            "weekly_consistency": weekly_consistency,
            "insights_text": insights_text,
            "motivation_message": motivation_message,
            "behavioral_observations": behavioral_observations or [],
            "report_style": report_style,
            "generation_model": generation_model,
        }

        stmt = (
            pg_insert(DailyReport)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_daily_reports_user_date",
                set_={
                    k: v for k, v in values.items()
                    if k not in ("user_id", "report_date")
                },
            )
            .returning(DailyReport)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 30,
        offset: int = 0,
    ) -> list[DailyReport]:
        """Get report history, newest first."""
        stmt = (
            select(DailyReport)
            .where(DailyReport.user_id == user_id)
            .order_by(desc(DailyReport.report_date))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_shown(self, report: DailyReport) -> DailyReport:
        """Mark a report as viewed."""
        report.was_shown = True
        report.shown_at = datetime.now(timezone.utc)
        await self.session.flush()
        return report

    async def set_rating(self, report: DailyReport, rating: int) -> DailyReport:
        """Store user's rating (1-5)."""
        report.user_rating = rating
        await self.session.flush()
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
        self.session.add(event)
        await self.session.flush()
        return event
