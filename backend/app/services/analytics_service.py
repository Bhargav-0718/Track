"""
AnalyticsService — behavioral metrics computed from existing MongoDB documents.

All metrics are derived by querying food_logs, workout_logs, and daily_summaries.
SQL aggregations replaced with Python-side aggregation over Beanie results.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from uuid import UUID

from app.core.logging import get_logger
from app.models.correction_event import CorrectionEvent
from app.models.daily_summary import DailySummary
from app.models.food_log import FoodLog
from app.models.progress_checkpoint import ProgressCheckpoint
from app.models.user import User
from app.models.workout_log import WorkoutLog
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


def _day_start(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time()).replace(tzinfo=dt_timezone.utc)


def _day_end(d: date) -> datetime:
    return _day_start(d) + timedelta(days=1)


class AnalyticsService:
    def __init__(self) -> None:
        pass

    # ── Public API ─────────────────────────────────────────────────────────────

    async def get_summary(self, user_id: UUID) -> AnalyticsSummary:
        today = date.today()

        user = await self._get_user(user_id)
        target_cal = user.target_calories if user else None
        target_prot = user.target_protein_g if user else None

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

    async def get_trend(self, user_id: UUID, period_days: int = 30) -> TrendResponse:
        today = date.today()
        start = today - timedelta(days=period_days - 1)

        user = await self._get_user(user_id)
        target_cal = user.target_calories if user else None
        target_prot = user.target_protein_g if user else None

        summaries_list = await DailySummary.find(
            DailySummary.user_id == user_id,
        ).to_list()
        summaries = {
            s.date: s for s in summaries_list
            if start <= s.date <= today
        }

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

    async def compute_report_context_metrics(self, user_id: UUID, report_date: date) -> dict:
        user = await self._get_user(user_id)
        target_cal = user.target_calories if user else None
        target_prot = user.target_protein_g if user else None

        nutrition = await self._get_day_nutrition(user_id, report_date)
        workouts = await self._get_day_workouts(user_id, report_date)
        streak = await self._compute_streak(user_id, report_date)
        consistency_7d = await self._compute_consistency(
            user_id, report_date, period_days=7,
            target_calories=target_cal, target_protein=target_prot,
        )
        accuracy = await self._compute_estimation_accuracy(user_id)
        meal_patterns = await self._compute_meal_patterns(user_id, report_date)
        patterns = self._generate_pattern_sentences(streak, consistency_7d, meal_patterns, report_date)

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
        return await User.get(user_id)

    async def _compute_streak(self, user_id: UUID, reference_date: date) -> StreakInfo:
        """Compute current and longest logging streaks."""
        start = reference_date - timedelta(days=364)

        summaries = await DailySummary.find(
            DailySummary.user_id == user_id,
        ).to_list()

        logged_dates: set[date] = {
            s.date for s in summaries
            if start <= s.date <= reference_date and (s.food_log_count or 0) > 0
        }

        # Current streak: walk backwards from reference_date
        current_streak = 0
        d = reference_date
        while d in logged_dates:
            current_streak += 1
            d -= timedelta(days=1)

        # Longest streak: scan full 365-day window
        longest = 0
        running = 0
        for i in range(365):
            day = start + timedelta(days=i)
            if day in logged_dates:
                running += 1
                longest = max(longest, running)
            else:
                running = 0

        last_logged = max(logged_dates) if logged_dates else None
        streak_start = (
            reference_date - timedelta(days=current_streak - 1)
            if current_streak > 0 else None
        )
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
        start = reference_date - timedelta(days=period_days - 1)
        label = "7d" if period_days == 7 else "30d"

        summaries_all = await DailySummary.find(
            DailySummary.user_id == user_id,
        ).to_list()
        summaries = [s for s in summaries_all if start <= s.date <= reference_date]

        days_logged = sum(1 for s in summaries if (s.food_log_count or 0) > 0)
        logging_consistency = days_logged / period_days

        cal_scores: list[float] = []
        prot_scores: list[float] = []
        workout_days = 0

        for s in summaries:
            if (s.food_log_count or 0) == 0:
                continue

            if target_calories and target_calories > 0 and s.total_calories_in:
                ratio = s.total_calories_in / target_calories
                cal_scores.append(max(0.0, 1.0 - abs(1.0 - ratio) * 2))

            if target_protein and target_protein > 0 and s.total_protein_g:
                ratio = s.total_protein_g / target_protein
                prot_scores.append(max(0.0, 1.0 - abs(1.0 - ratio) * 2))

            if (s.workout_count or 0) > 0:
                workout_days += 1

        cal_adherence = sum(cal_scores) / len(cal_scores) if cal_scores else 0.5
        prot_adherence = sum(prot_scores) / len(prot_scores) if prot_scores else 0.5
        target_workouts = (period_days / 7) * 4
        workout_consistency = min(workout_days / max(target_workouts, 1), 1.0)

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
        start = reference_date - timedelta(days=period_days - 1)
        start_dt = _day_start(start)
        end_dt = _day_end(reference_date)

        logs = await FoodLog.find(
            FoodLog.user_id == user_id,
            FoodLog.is_deleted == False,  # noqa: E712
            FoodLog.logged_at >= start_dt,
            FoodLog.logged_at < end_dt,
        ).to_list()

        # Group by meal_type
        meal_logs: dict[str, list[FoodLog]] = defaultdict(list)
        for log in logs:
            meal_logs[log.meal_type].append(log)

        # Top foods per meal type
        food_counts: dict[str, Counter] = defaultdict(Counter)
        for log in logs:
            food_counts[log.meal_type][log.food_name] += 1

        patterns = []
        for meal_type, meal_log_list in meal_logs.items():
            count = len(meal_log_list)
            avg_cal = sum(l.calories for l in meal_log_list) / count if count else 0.0
            freq = min(count / period_days, 1.0)
            top_foods = [f for f, _ in food_counts[meal_type].most_common(3)]
            patterns.append(MealAdherencePattern(
                meal_type=meal_type,
                log_frequency_pct=round(freq * 100, 1),
                avg_calories=round(avg_cal, 1),
                most_common_foods=top_foods,
            ))

        return sorted(patterns, key=lambda p: p.log_frequency_pct, reverse=True)

    async def _compute_estimation_accuracy(self, user_id: UUID) -> EstimationAccuracyStats:
        period_start = date.today() - timedelta(days=30)
        period_start_dt = _day_start(period_start)

        logs = await FoodLog.find(
            FoodLog.user_id == user_id,
            FoodLog.is_deleted == False,  # noqa: E712
            FoodLog.logged_at >= period_start_dt,
        ).to_list()

        total_logs = len(logs)
        corrected_logs = sum(1 for l in logs if l.is_corrected)

        # Average calorie delta from correction events
        corrections = await CorrectionEvent.find(
            CorrectionEvent.user_id == user_id,
            CorrectionEvent.correction_type == "calories",
        ).to_list()
        deltas = [abs(c.delta) for c in corrections if c.delta is not None]
        avg_delta = sum(deltas) / len(deltas) if deltas else 0.0

        # Source breakdown
        source_breakdown: dict[str, int] = defaultdict(int)
        for log in logs:
            source_breakdown[log.estimation_source] += 1

        correction_rate = (corrected_logs / total_logs * 100) if total_logs > 0 else 0.0

        return EstimationAccuracyStats(
            total_logs=total_logs,
            corrected_logs=corrected_logs,
            correction_rate_pct=round(correction_rate, 1),
            avg_calorie_delta=round(avg_delta, 1),
            source_breakdown=dict(source_breakdown),
        )

    async def _get_day_nutrition(self, user_id: UUID, target_date: date) -> dict:
        logs = await FoodLog.find(
            FoodLog.user_id == user_id,
            FoodLog.is_deleted == False,  # noqa: E712
            FoodLog.logged_at >= _day_start(target_date),
            FoodLog.logged_at < _day_end(target_date),
        ).to_list()

        return {
            "calories": sum(l.calories for l in logs),
            "protein": sum(l.protein_g or 0.0 for l in logs),
            "carbs": sum(l.carbs_g or 0.0 for l in logs),
            "fat": sum(l.fat_g or 0.0 for l in logs),
            "meal_count": len(logs),
        }

    async def _get_day_workouts(self, user_id: UUID, target_date: date) -> dict:
        logs = await WorkoutLog.find(
            WorkoutLog.user_id == user_id,
            WorkoutLog.is_deleted == False,  # noqa: E712
            WorkoutLog.logged_at >= _day_start(target_date),
            WorkoutLog.logged_at < _day_end(target_date),
        ).to_list()

        types = list({l.workout_type for l in logs})
        return {
            "count": len(logs),
            "calories_burned": sum(l.calories_burned or 0.0 for l in logs),
            "duration_minutes": sum(l.duration_minutes for l in logs),
            "types": types,
        }

    async def _weight_trend(
        self,
        user_id: UUID,
        reference_date: date,
        period_days: int,
    ) -> tuple[int, float | None, float | None]:
        start = reference_date - timedelta(days=period_days)

        all_checkpoints = await ProgressCheckpoint.find(
            ProgressCheckpoint.user_id == user_id,
            ProgressCheckpoint.is_deleted == False,  # noqa: E712
        ).to_list()

        total = len(all_checkpoints)

        in_range = [
            c for c in all_checkpoints
            if start <= c.checkpoint_date <= reference_date and c.weight_kg is not None
        ]
        in_range.sort(key=lambda c: c.checkpoint_date)

        if not in_range:
            return total, None, None

        earliest_weight = in_range[0].weight_kg
        latest_weight = in_range[-1].weight_kg
        weight_change = (latest_weight - earliest_weight) if earliest_weight else None

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
        insights = []

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

        if consistency_7d.logging_consistency > consistency_30d.logging_consistency + 0.15:
            insights.append(
                "Your logging consistency has improved noticeably this week compared to last month."
            )
        elif consistency_7d.logging_consistency < consistency_30d.logging_consistency - 0.15:
            insights.append(
                "Your logging frequency dipped this week. "
                "Getting back on track usually takes just one logged meal."
            )

        if consistency_7d.calorie_adherence >= 0.85:
            insights.append("You've been hitting your calorie target consistently this week.")
        elif consistency_7d.calorie_adherence < 0.50:
            insights.append(
                "Your calorie intake has been variable this week. "
                "Logging every meal helps build a more accurate picture."
            )

        if consistency_7d.protein_adherence < 0.70 and consistency_7d.logging_consistency > 0.7:
            insights.append(
                "You log consistently but protein tends to fall short of your target. "
                "Adding a protein source to one meal can make a big difference."
            )

        if meal_patterns:
            worst = min(meal_patterns, key=lambda p: p.log_frequency_pct)
            if worst.log_frequency_pct < 40:
                insights.append(
                    f"You log {worst.meal_type.replace('_', ' ')} only "
                    f"{worst.log_frequency_pct:.0f}% of days — "
                    f"it's your most commonly missed meal."
                )

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

        return insights[:6]

    def _generate_pattern_sentences(
        self,
        streak: StreakInfo,
        consistency_7d: ConsistencyBreakdown,
        meal_patterns: list[MealAdherencePattern],
        report_date: date,
    ) -> list[str]:
        patterns = []

        if streak.current_streak_days >= 3:
            patterns.append(f"Current logging streak: {streak.current_streak_days} consecutive days.")

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
                    f"Tends to skip logging {worst.meal_type.replace('_', ' ')} most days."
                )
            best = max(meal_patterns, key=lambda p: p.log_frequency_pct)
            if best.log_frequency_pct >= 80:
                patterns.append(
                    f"Very consistent at logging {best.meal_type.replace('_', ' ')} "
                    f"({best.log_frequency_pct:.0f}% of days)."
                )

        return patterns[:5]
