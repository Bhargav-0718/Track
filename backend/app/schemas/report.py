"""
Schemas for Phase 4 — Daily AI Reports.

DailyReport is the primary output of the adaptive reporting system.
It's generated nightly and includes:
  - Computed nutrition/workout summaries
  - AI-generated narrative (style adapts to user preference)
  - Behavioral observations (pattern-based, heuristic)
  - Motivational message

The user can rate reports (1-5), which trains future style selection.
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import TrackBaseSchema


# ── Report Style ───────────────────────────────────────────────────────────────

ReportStyle = Literal["motivational", "analytical", "brief", "detailed"]


# ── Sub-schemas for computed summaries ────────────────────────────────────────

class CalorieSummary(TrackBaseSchema):
    """Nutrition summary for the day."""
    target_calories: float
    actual_calories: float
    adherence_pct: float           # 0-100
    deficit_or_surplus: float      # negative = deficit, positive = surplus
    protein_g: float
    protein_target_g: float
    protein_adherence_pct: float
    carbs_g: float
    fat_g: float
    meals_logged: int


class WorkoutSummaryData(TrackBaseSchema):
    """Workout summary for the day."""
    workouts_completed: int
    total_calories_burned: float
    net_calories: float            # actual_calories - calories_burned
    workout_types: list[str]       # e.g., ["strength", "cardio"]
    total_duration_minutes: float
    rest_day: bool                 # True if no workouts


# ── Report Schemas ─────────────────────────────────────────────────────────────

class DailyReportResponse(TrackBaseSchema):
    """Full daily report response."""
    id: UUID
    report_date: date

    # Computed metrics
    calorie_summary: dict
    workout_summary: dict
    macro_summary: dict
    consistency_score: float        # 0.0–1.0
    streak_days: int
    weekly_consistency: float       # 0.0–1.0

    # AI-generated content
    insights_text: str | None = None
    motivation_message: str | None = None
    behavioral_observations: list[str] = Field(default_factory=list)

    # Report metadata
    report_style: ReportStyle
    generation_model: str

    # Engagement
    was_shown: bool
    shown_at: datetime | None = None
    user_rating: int | None = None

    created_at: datetime


class DailyReportSummary(TrackBaseSchema):
    """Lightweight report for history list."""
    id: UUID
    report_date: date
    consistency_score: float
    streak_days: int
    insights_text: str | None = None    # Truncated to first 200 chars in service
    was_shown: bool
    user_rating: int | None = None
    created_at: datetime


class ReportRateRequest(TrackBaseSchema):
    """User rates a report."""
    rating: int = Field(ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)")


class ReportGenerateRequest(TrackBaseSchema):
    """
    Manually trigger report generation for a specific date.
    Useful for testing and backfilling.

    By default, generates for today in the user's timezone.
    """
    report_date: date | None = Field(
        default=None,
        description="Date to generate report for (defaults to today)"
    )
    report_style: ReportStyle | None = Field(
        default=None,
        description="Override user's preferred style for this generation"
    )
    force_regenerate: bool = Field(
        default=False,
        description="Regenerate even if a report already exists for this date"
    )


class ReportMarkShownRequest(TrackBaseSchema):
    """Mark a report as viewed."""
    pass  # No body needed — presence of the request is sufficient
