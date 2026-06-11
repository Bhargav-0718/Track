"""
UserPreference request/response schemas.
"""
from app.schemas.common import TrackBaseSchema
from app.schemas.report import ReportStyle


class UserPreferenceResponse(TrackBaseSchema):
    """Current user preferences relevant to AI reports."""
    preferred_report_style: ReportStyle
    report_enabled: bool


class UserPreferenceUpdate(TrackBaseSchema):
    """Body for PUT /api/v1/users/me/preferences — all fields optional."""
    preferred_report_style: ReportStyle | None = None
    report_enabled: bool | None = None
