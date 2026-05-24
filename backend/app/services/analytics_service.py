"""
AnalyticsService — behavioral metrics computed from existing data.

NO machine learning, NO separate analytics tables.
All metrics are derived by querying food_logs, workout_logs, and daily_reports
that already exist. This is intentionally simple — heuristics over complexity.

Metrics computed:
  - Logging streak (current + longest)
  - Consistency scores (7d and 30d)
  - Calorie adherence
  - Protein adherence
  - Workout consistency
  - Meal pattern analysis (which meals get logged vs skipped)
  - Estimation accuracy (correction rate from AI pipeline)
  - Behavioral pattern sentences (human-readable, ready for AI prompt injection)

Phase 4: These metrics feed both the analytics endpoint AND the daily report generator.
"""
from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.correction_event import CorrectionEvent
from app.models.daily_summary import DailySummary
from app.models.food_log import FoodLog
from app.models.progress_checkpoint import ProgressCheckpoint
from app.models.workout_log import WorkoutLog
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummary,
    ConsistencyBreakdown,
    DailyDataPoint,
    EstimationAccuracyStats,
    MealAdherencePattern,
    StreakInfo,
    TrendResponse,
)

logger = get_logger(__name__)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Public API ─────────────────────────────────────────────────────────────

    async def get_summary(self, user_id: UUID) -> AnalyticsSummary:
        """
        Full behavioral analytics snapshot.
        Queries run in parallel via separate DB calls (no join complexity).
        """
        today = date.today()

        # Fetch user for target calories/protein
        user = await self._get_user(user_id)
        target_cal = user.target_calories if user else None
        target_prot = user.target_protein_g if user else None

        # Compute all metrics
        streak = await self._compute_streak(user_id, today)
        consistency_7d = await self._compute_consistency(
            user_id, today, period_days=7,
            target_calories=target_cal, target_protein=target_prot
        )
        consistency_30d = await self._compute_consistency(
            user_id, today, period_days=30,
            target_calories=target_cal, target_protein=target_prot
        )
        meal_patterns = await self._compute_meal_patterns(user_id, today)
        estimation_accuracy = await self._compute_estimation_accuracy(user_id)
        pattern_insights = self._generate_pattern_insights(
            streak, consistency_7d, consistency_30d, meal_patterns, estimation_accuracy
        )

        # Weight data from checkpoints
        checkpoints_count, latest_weight, weight_trend = await self._weight_trend(
            user_id, today, period_days=30
        )

        return AnalyticsSummary(
            user_id=user_id,
            streak=streak,
            consistency_7d=consistency_7d,
            consistency_30d=consistency_30d,
            meal_patterns=meal_patterns,
            estimation_accuracy=estimation_accuracy,
            pattern_insights=pattern_insights,
            checkpoints_count=checkpoints_count,
            latest_weight_kg=latest_weight,
            weight_trend_kg=weight_trend,
            computed_at=today,
        )

    async def get_trend(
        self,
        user_id: UUID,
        period_days: int = 30,
    ) -> TrendResponse:
        """
        Time-series data for trend charts.
        Returns one data point per day for the last N days.
        """
        today = date.today()
        start = today - timedelta(days=period_days - 1)

        user = await self._get_user(user_id)
        target_cal = user.target_calories if user else None
        target_prot = user.target_protein_g if user else None

        # Build a date → summary dict from daily_summaries table
        stmt = select(DailySummary).where(
            and_(
                DailySummary.user_id == user_id,
                DailySummary.date >= start,
                DailySummary.date <= today,
            )
        )
        result = await self.session.execute(stmt)
        summaries = {s.date: s for s in result.scalars().all()}

        data_points = []
        total_calories = 0.0
        total_protein = 0.0
        logged_days = 0

        for i in range(period_days):
            d = start + timedelta(days=i)
            summary = summaries.get(d)

            if summary:
                cal = summary.total_calories_in or 0.0
                prot = summary.total_protein_g or 0.0
                workouts = summary.workout_count or 0
                logged = (summary.food_log_count or 0) > 0
                total_calories += cal
                total_protein += prot
                if logged:
                    logged_days += 1
            else:
                cal, prot, workouts, logged = 0.0, 0.0, 0, False

            data_points.append(DailyDataPoint(
                date=d,
                calories=cal,
                protein_g=prot if prot > 0 else None,
                workouts=workouts,
                logged=logged,
            ))

        avg_cal = total_calories / max(logged_days, 1)
        avg_prot = total_protein / max(logged_days, 1) if total_protein > 0 else None

        return TrendResponse(
            period_days=period_days,
            data_points=data_points,
            calorie_target=target_cal,
            protein_target_g=target_prot,
            average_calories=round(avg_cal, 1),
            average_protein_g=round(avg_prot, 1) if avg_prot else None,
        )

    async def compute_report_context_metrics(
        self,
        user_id: UUID,
        report_date: date,
    ) -> dict:
        """
        Compute all metrics needed for daily report generation.
        Returns a flat dict ready to populate ReportContext.
        Used by ReportService before calling generate_daily_report().
        """
        user = await self._get_user(user_id)
        target_cal = user.target_calories if user else None
        target_prot = user.target_protein_g if user else None

        # Today's nutrition from food_logs directly (more accurate than daily_summary)
        nutrition = await self._get_day_nutrition(user_id, report_date)

        # Today's workouts
        workouts = await self._get_day_workouts(user_id, report_date)

        # Streak
        streak = await self._compute_streak(user_id, report_date)

        # 7-day consistency
        consistency_7d = await self._compute_consistency(
            user_id, report_date, period_days=7,
            target_calories=target_cal, target_protein=target_prot,
        )

        # Correction rate (last 30 days)
        accuracy = await self._compute_estimation_accuracy(user_id)

        # Generate pattern sentences (ready for AI prompt injection)
        meal_patterns = await self._compute_meal_patterns(user_id, report_date)
        patterns = self._generate_pattern_sentences(
            streak, consistency_7d, meal_patterns, report_date
        )

        return {
            "goal": user.goal if user else "maintain",
            "target_calories": target_cal,
            "target_protein_g": target_prot,
            "actual_calories": nutrition["calories"],
            "actual_protein_g": nutrition["protein"],
            "actual_carbs_g": nutrition["carbs"],
            "actual_fat_g": nutrition["fat"],
            "meals_logged": nutrition["meal_count"],
            "workouts_completed": workouts["count"],
            "total_calories_burned": workouts["calories_burned"],
            "workout_types": workouts["types"],
            "workout_duration_minutes": workouts["duration_minutes"],
            "streak_days": streak.current_streak_days,
            "consistency_7d": consistency_7d.logging_consistency,
            "calorie_adherence_7d": consistency_7d.calorie_adherence,
            "protein_adherence_7d": consistency_7d.protein_adherence,
            "correction_rate_pct": accuracy.correction_rate_pct,
            "behavioral_patterns": patterns,
        }

    # ── Internal Computations ──────────────────────────────────────────────────

    async def _get_user(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _compute_streak(self, user_id: UUID, reference_date: date) -> StreakInfo:
        """
        Compute current and longest logging streaks by scanning daily_summaries.
        A day counts as "logged" if food_log_count > 0.
        """
        # Fetch last 365 days of daily_summaries
        start = reference_date - timedelta(days=364)
        stmt = (
            select(DailySummary.date, DailySummary.food_log_count)
            .where(
                and_(
                    DailySummary.user_id == user_id,
                    DailySummary.date >= start,
                    DailySummary.date <= reference_date,
                )
            )
            .order_by(DailySummary.date.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        logged_dates: set[date] = {
            row.date for row in rows if (row.food_log_count or 0) > 0
        }

        # Walk backwards from reference_date to find current streak
        current_streak = 0
        d = reference_date
        while d in logged_dates:
            current_streak += 1
            d -= timedelta(days=1)

        # Longest streak (full 365-day scan)
        longest = 0
        running = 0
        for i in range(364, -1, -1):
            day = start + timedelta(days=i)
            if day in logged_dates:
                running += 1
                longest = max(longest, running)
            else:
                running = 0

        last_logged = max(logged_dates) if logged_dates else None
        streak_start = (reference_date - timedelta(days=current_streak - 1)
                        if current_streak > 0 else None)
        is_active = reference_date in logged_dates

        return StreakInfo(
            current_streak_days=current_streak,
            longest_streak_days=longest,
            streak_started_on=streak_start,
            last_logged_date=last_logged,
            is_active_today=is_active,
        )

    async def _compute_consistency(
        self,
        user_id: UUID,
        reference_date: date,
        period_days: int,
        target_calories: float | None,
        target_protein: float | None,
    ) -> ConsistencyBreakdown:
        """
        Compute multi-dimensional consistency for a rolling window.
        """
        start = reference_date - timedelta(days=period_days - 1)
        label = "7d" if period_days == 7 else "30d"

        # Fetch daily_summaries for the period
        stmt = select(DailySummary).where(
            and_(
                DailySummary.user_id == user_id,
                DailySummary.date >= start,
                DailySummary.date <= reference_date,
            )
        )
        result = await self.session.execute(stmt)
        summaries = list(result.scalars().all())

        days_logged = sum(1 for s in summaries if (s.food_log_count or 0) > 0)
        logging_consistency = days_logged / period_days

        # Calorie adherence: 1.0 if within ±15% of target
        cal_scores = []
        prot_scores = []
        workout_days = 0

        for s in summaries:
            if (s.food_log_count or 0) == 0:
                continue  # Don't penalize unlogged days in adherence (already in logging)

            if target_calories and target_calories > 0 and s.total_calories_in:
                ratio = s.total_calories_in / target_calories
                # Score: 1.0 at ratio=1.0, decays toward 0 as ratio deviates
                score = max(0.0, 1.0 - abs(1.0 - ratio) * 2)
                cal_scores.append(score)

            if target_protein and target_protein > 0 and s.total_protein_g:
                ratio = s.total_protein_g / target_protein
                score = max(0.0, 1.0 - abs(1.0 - ratio) * 2)
                prot_scores.append(score)

            if (s.workout_count or 0) > 0:
                workout_days += 1

        cal_adherence = sum(cal_scores) / len(cal_scores) if cal_scores else 0.5
        prot_adherence = sum(prot_scores) / len(prot_scores) if prot_scores else 0.5
        # Workout consistency: assume 4 workouts/week target as baseline
        target_workouts = (period_days / 7) * 4
        workout_consistency = min(workout_days / max(target_workouts, 1), 1.0)

        # Weighted composite: logging is most important
        overall = (
            logging_consistency * 0.40
            + cal_adherence * 0.25
            + prot_adherence * 0.20
            + workout_consistency * 0.15
        )

        return ConsistencyBreakdown(
            overall_score=round(overall, 3),
            logging_consistency=round(logging_consistency, 3),
            calorie_adherence=round(cal_adherence, 3),
            protein_adherence=round(prot_adherence, 3),
            workout_consistency=round(workout_consistency, 3),
            period_days=period_days,
            period_label=label,  # type: ignore[arg-type]
            days_logged=days_logged,
            days_in_period=period_days,
            workouts_completed=workout_days,
        )

    async def _compute_meal_patterns(
        self,
        user_id: UUID,
        reference_date: date,
        period_days: int = 30,
    ) -> list[MealAdherencePattern]:
        """
        Analyse which meals are logged most/least consistently.
        """
        start = reference_date - timedelta(days=period_days - 1)

        # Count logs per meal type
        stmt = (
            select(
                FoodLog.meal_type,
                func.count(FoodLog.id).label("log_count"),
                func.avg(FoodLog.calories).label("avg_cal"),
            )
            .where(
                and_(
                    FoodLog.user_id == user_id,
                    FoodLog.is_deleted.is_(False),
                    func.date(FoodLog.logged_at) >= start,
                )
            )
            .group_by(FoodLog.meal_type)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # Most common foods per meal type
        food_stmt = (
            select(FoodLog.meal_type, FoodLog.food_name, func.count(FoodLog.id).label("cnt"))
            .where(
                and_(
                    FoodLog.user_id == user_id,
                    FoodLog.is_deleted.is_(False),
                )
            )
            .group_by(FoodLog.meal_type, FoodLog.food_name)
            .order_by(FoodLog.meal_type, func.count(FoodLog.id).desc())
        )
        food_result = await self.session.execute(food_stmt)
        food_rows = food_result.all()

        # Group top foods per meal type
        top_foods: dict[str, list[str]] = defaultdict(list)
        counts_per_meal: dict[str, int] = defaultdict(int)
        for row in food_rows:
            counts_per_meal[row.meal_type] += 1
            if len(top_foods[row.meal_type]) < 3:
                top_foods[row.meal_type].append(row.food_name)

        patterns = []
        for row in rows:
            meal = row.meal_type
            freq = min(row.log_count / period_days, 1.0)
            patterns.append(MealAdherencePattern(
                meal_type=meal,
                log_frequency_pct=round(freq * 100, 1),
                avg_calories=round(row.avg_cal or 0, 1),
                most_common_foods=top_foods.get(meal, []),
            ))

        return sorted(patterns, key=lambda p: p.log_frequency_pct, reverse=True)

    async def _compute_estimation_accuracy(self, user_id: UUID) -> EstimationAccuracyStats:
        """
        How often did the user correct AI estimates?
        High correction rate → AI needs more personal data (more logs = better).
        """
        period_start = date.today() - timedelta(days=30)

        # Total logs in last 30 days
        total_stmt = select(func.count(FoodLog.id)).where(
            and_(
                FoodLog.user_id == user_id,
                FoodLog.is_deleted.is_(False),
                func.date(FoodLog.logged_at) >= period_start,
            )
        )
        total_logs = (await self.session.execute(total_stmt)).scalar_one() or 0

        # Corrected logs
        corrected_stmt = select(func.count(FoodLog.id)).where(
            and_(
                FoodLog.user_id == user_id,
                FoodLog.is_deleted.is_(False),
                FoodLog.is_corrected.is_(True),
                func.date(FoodLog.logged_at) >= period_start,
            )
        )
        corrected_logs = (await self.session.execute(corrected_stmt)).scalar_one() or 0

        # Average calorie delta from correction events
        delta_stmt = select(func.avg(func.abs(CorrectionEvent.delta))).where(
            and_(
                CorrectionEvent.user_id == user_id,
                CorrectionEvent.correction_type == "calories",
            )
        )
        avg_delta = (await self.session.execute(delta_stmt)).scalar_one() or 0.0

        # Source breakdown
        source_stmt = (
            select(FoodLog.estimation_source, func.count(FoodLog.id).label("cnt"))
            .where(
                and_(
                    FoodLog.user_id == user_id,
                    FoodLog.is_deleted.is_(False),
                    func.date(FoodLog.logged_at) >= period_start,
                )
            )
            .group_by(FoodLog.estimation_source)
        )
        source_result = await self.session.execute(source_stmt)
        source_breakdown = {row.estimation_source: row.cnt for row in source_result.all()}

        correction_rate = (corrected_logs / total_logs * 100) if total_logs > 0 else 0.0

        return EstimationAccuracyStats(
            total_logs=total_logs,
            corrected_logs=corrected_logs,
            correction_rate_pct=round(correction_rate, 1),
            avg_calorie_delta=round(float(avg_delta), 1),
            source_breakdown=source_breakdown,
        )

    async def _get_day_nutrition(self, user_id: UUID, target_date: date) -> dict:
        """Get aggregated nutrition for a specific date."""
        stmt = select(
            func.coalesce(func.sum(FoodLog.calories), 0.0).label("calories"),
            func.coalesce(func.sum(FoodLog.protein_g), 0.0).label("protein"),
            func.coalesce(func.sum(FoodLog.carbs_g), 0.0).label("carbs"),
            func.coalesce(func.sum(FoodLog.fat_g), 0.0).label("fat"),
            func.count(FoodLog.id).label("meal_count"),
        ).where(
            and_(
                FoodLog.user_id == user_id,
                FoodLog.is_deleted.is_(False),
                func.date(FoodLog.logged_at) == target_date,
            )
        )
        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "calories": float(row.calories),
            "protein": float(row.protein),
            "carbs": float(row.carbs),
            "fat": float(row.fat),
            "meal_count": row.meal_count,
        }

    async def _get_day_workouts(self, user_id: UUID, target_date: date) -> dict:
        """Get workout summary for a specific date."""
        stmt = select(
            func.count(WorkoutLog.id).label("count"),
            func.coalesce(func.sum(WorkoutLog.calories_burned), 0.0).label("calories_burned"),
            func.coalesce(func.sum(WorkoutLog.duration_minutes), 0.0).label("duration"),
        ).where(
            and_(
                WorkoutLog.user_id == user_id,
                WorkoutLog.is_deleted.is_(False),
                func.date(WorkoutLog.logged_at) == target_date,
            )
        )
        result = await self.session.execute(stmt)
        row = result.one()

        # Get workout types for the day
        types_stmt = (
            select(WorkoutLog.workout_type)
            .where(
                and_(
                    WorkoutLog.user_id == user_id,
                    WorkoutLog.is_deleted.is_(False),
                    func.date(WorkoutLog.logged_at) == target_date,
                )
            )
            .distinct()
        )
        types_result = await self.session.execute(types_stmt)
        types = [r.workout_type for r in types_result.all()]

        return {
            "count": row.count,
            "calories_burned": float(row.calories_burned),
            "duration_minutes": float(row.duration),
            "types": types,
        }

    async def _weight_trend(
        self,
        user_id: UUID,
        reference_date: date,
        period_days: int,
    ) -> tuple[int, float | None, float | None]:
        """
        Return (checkpoint_count, latest_weight_kg, weight_change_kg) from
        ProgressCheckpoint records within the period.
        """
        start = reference_date - timedelta(days=period_days)
        stmt = (
            select(ProgressCheckpoint.checkpoint_date, ProgressCheckpoint.weight_kg)
            .where(
                and_(
                    ProgressCheckpoint.user_id == user_id,
                    ProgressCheckpoint.is_deleted.is_(False),
                    ProgressCheckpoint.checkpoint_date >= start,
                    ProgressCheckpoint.checkpoint_date <= reference_date,
                    ProgressCheckpoint.weight_kg.is_not(None),
                )
            )
            .order_by(ProgressCheckpoint.checkpoint_date)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            total_count_stmt = select(func.count(ProgressCheckpoint.id)).where(
                and_(
                    ProgressCheckpoint.user_id == user_id,
                    ProgressCheckpoint.is_deleted.is_(False),
                )
            )
            total = (await self.session.execute(total_count_stmt)).scalar_one()
            return total, None, None

        earliest_weight = rows[0].weight_kg
        latest_weight = rows[-1].weight_kg
        weight_change = (latest_weight - earliest_weight) if earliest_weight else None

        total_count_stmt = select(func.count(ProgressCheckpoint.id)).where(
            and_(
                ProgressCheckpoint.user_id == user_id,
                ProgressCheckpoint.is_deleted.is_(False),
            )
        )
        total = (await self.session.execute(total_count_stmt)).scalar_one()

        return total, latest_weight, weight_change

    # ── Heuristic Pattern Generation ───────────────────────────────────────────

    def _generate_pattern_insights(
        self,
        streak: StreakInfo,
        consistency_7d: ConsistencyBreakdown,
        consistency_30d: ConsistencyBreakdown,
        meal_patterns: list[MealAdherencePattern],
        accuracy: EstimationAccuracyStats,
    ) -> list[str]:
        """
        Generate human-readable insight sentences from computed metrics.
        These appear in the analytics endpoint.
        """
        insights = []

        # Streak observations
        if streak.current_streak_days >= 7:
            insights.append(
                f"You're on a {streak.current_streak_days}-day logging streak — "
                f"that's your best consistency indicator."
            )
        elif streak.current_streak_days >= 3:
            insights.append(
                f"You've logged for {streak.current_streak_days} days in a row. "
                f"Keep going — consistency is the foundation of progress."
            )
        elif streak.longest_streak_days > streak.current_streak_days:
            insights.append(
                f"Your longest logging streak was {streak.longest_streak_days} days. "
                f"You're at {streak.current_streak_days} now — you can beat it."
            )

        # Consistency deltas
        if consistency_7d.logging_consistency > consistency_30d.logging_consistency + 0.15:
            insights.append(
                "Your logging consistency has improved noticeably this week compared to last month."
            )
        elif consistency_7d.logging_consistency < consistency_30d.logging_consistency - 0.15:
            insights.append(
                "Your logging frequency dipped this week. "
                "Getting back on track usually takes just one logged meal."
            )

        # Calorie adherence
        if consistency_7d.calorie_adherence >= 0.85:
            insights.append("You've been hitting your calorie target consistently this week.")
        elif consistency_7d.calorie_adherence < 0.50:
            insights.append(
                "Your calorie intake has been variable this week. "
                "Logging every meal helps build a more accurate picture."
            )

        # Protein adherence
        if consistency_7d.protein_adherence < 0.70 and consistency_7d.logging_consistency > 0.7:
            insights.append(
                "You log consistently but protein tends to fall short of your target. "
                "Adding a protein source to one meal can make a big difference."
            )

        # Meal patterns — find the least-logged meal
        if meal_patterns:
            worst = min(meal_patterns, key=lambda p: p.log_frequency_pct)
            if worst.log_frequency_pct < 40:
                insights.append(
                    f"You log {worst.meal_type.replace('_', ' ')} only "
                    f"{worst.log_frequency_pct:.0f}% of days — "
                    f"it's your most commonly missed meal."
                )

        # Estimation accuracy
        if accuracy.correction_rate_pct > 30:
            insights.append(
                f"You've corrected {accuracy.correction_rate_pct:.0f}% of AI estimates recently. "
                f"The more you log, the more accurate the AI becomes for your foods."
            )
        elif accuracy.correction_rate_pct < 10 and accuracy.total_logs > 20:
            insights.append(
                "The AI estimates are matching your corrections closely — "
                "your food memory is well-trained."
            )

        return insights[:6]  # Cap at 6 insights for readability

    def _generate_pattern_sentences(
        self,
        streak: StreakInfo,
        consistency_7d: ConsistencyBreakdown,
        meal_patterns: list[MealAdherencePattern],
        report_date: date,
    ) -> list[str]:
        """
        Shorter pattern sentences for injection into AI report prompts.
        These become the "DETECTED BEHAVIORAL PATTERNS" in the prompt.
        """
        patterns = []

        if streak.current_streak_days >= 3:
            patterns.append(
                f"Current logging streak: {streak.current_streak_days} consecutive days."
            )

        if consistency_7d.logging_consistency >= 0.86:
            patterns.append("Logged food on 6+ of the last 7 days — highly consistent.")
        elif consistency_7d.logging_consistency < 0.50:
            patterns.append("Logged food on fewer than half the days this week.")

        if consistency_7d.calorie_adherence >= 0.85:
            patterns.append("Hit calorie target on most days this week.")
        elif consistency_7d.calorie_adherence < 0.50:
            patterns.append("Calorie intake has been well below target this week.")

        if consistency_7d.protein_adherence < 0.65:
            patterns.append(
                "Protein has been consistently below target this week — "
                "tends to happen on rest days or days with fewer meals."
            )

        if meal_patterns:
            worst = min(meal_patterns, key=lambda p: p.log_frequency_pct)
            if worst.log_frequency_pct < 40:
                patterns.append(
                    f"Tends to skip logging {worst.meal_type.replace('_', ' ')} "
                    f"most days."
                )
            best = max(meal_patterns, key=lambda p: p.log_frequency_pct)
            if best.log_frequency_pct >= 80:
                patterns.append(
                    f"Very consistent at logging {best.meal_type.replace('_', ' ')} "
                    f"({best.log_frequency_pct:.0f}% of days)."
                )

        return patterns[:5]  # Keep prompts concise
