"""
Schemas for Phase 4 — Behavioral Analytics.

Analytics are computed on-demand from existing food_logs, workout_logs,
and daily_reports. No separate storage needed — the source tables ARE
the behavioral record.

Analytics cover:
  - Logging consistency (did user log every day?)
  - Calorie adherence (how close to target?)
  - Workout consistency (did user work out as planned?)
  - Streak tracking
  - Trend analysis (7-day, 30-day)
  - Correction rate (how often AI estimates were wrong)
"""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import TrackBaseSchema


# ── Streak Info ────────────────────────────────────────────────────────────────

class StreakInfo(TrackBaseSchema):
    """Current and best logging streak."""
    current_streak_days: int
    longest_streak_days: int
    streak_started_on: date | None = None
    last_logged_date: date | None = None
    is_active_today: bool           # Has the user logged anything today?


# ── Consistency Scores ─────────────────────────────────────────────────────────

class ConsistencyBreakdown(TrackBaseSchema):
    """
    Multi-dimensional consistency analysis.
    Scores are 0.0–1.0 (higher = more consistent).
    """
    # Overall weighted composite score
    overall_score: float

    # Component scores
    logging_consistency: float      # Days with ≥1 food log / total days
    calorie_adherence: float        # Closeness to calorie target (±15% = 1.0)
    protein_adherence: float        # Closeness to protein target
    workout_consistency: float      # Workouts logged / expected workouts

    # Period (days back from today)
    period_days: int                # 7 or 30
    period_label: Literal["7d", "30d"]

    # Raw counts for transparency
    days_logged: int
    days_in_period: int
    workouts_completed: int


# ── Trend Data ─────────────────────────────────────────────────────────────────

class DailyDataPoint(TrackBaseSchema):
    """Single day's data for trend charts."""
    date: date
    calories: float
    protein_g: float | None = None
    workouts: int
    logged: bool                    # Did user log any food this day?
    consistency_score: float | None = None   # From daily_report if generated


class TrendResponse(TrackBaseSchema):
    """Time-series data for trend visualization in Flutter charts."""
    period_days: int
    data_points: list[DailyDataPoint]
    calorie_target: float | None = None
    protein_target_g: float | None = None
    average_calories: float
    average_protein_g: float | None = None


# ── Behavioral Patterns ────────────────────────────────────────────────────────

class MealAdherencePattern(TrackBaseSchema):
    """Which meals are logged most/least consistently."""
    meal_type: str
    log_frequency_pct: float        # % of days this meal was logged
    avg_calories: float
    most_common_foods: list[str]    # Top 3 foods logged for this meal


class EstimationAccuracyStats(TrackBaseSchema):
    """
    How well the AI estimation pipeline is performing.
    High correction_rate = AI needs more training data (more logs).
    """
    total_logs: int
    corrected_logs: int
    correction_rate_pct: float
    avg_calorie_delta: float        # Average absolute difference after correction
    source_breakdown: dict[str, int]   # {"memory": 45, "dataset": 30, "llm": 25}


# ── Summary Analytics ──────────────────────────────────────────────────────────

class AnalyticsSummary(TrackBaseSchema):
    """
    Complete behavioral analytics snapshot.
    Returned by GET /analytics/summary — the main analytics endpoint.
    """
    user_id: UUID

    # Streak
    streak: StreakInfo

    # Consistency (7-day and 30-day views)
    consistency_7d: ConsistencyBreakdown
    consistency_30d: ConsistencyBreakdown

    # Patterns
    meal_patterns: list[MealAdherencePattern]
    estimation_accuracy: EstimationAccuracyStats

    # Generated insights (heuristic, not AI)
    # e.g., ["You log breakfast 90% of days but skip lunch 40% of the time"]
    pattern_insights: list[str] = Field(default_factory=list)

    # Weight trend (from progress checkpoints, if any)
    checkpoints_count: int = 0
    latest_weight_kg: float | None = None
    weight_trend_kg: float | None = None    # Change since earliest checkpoint in period

    computed_at: date
