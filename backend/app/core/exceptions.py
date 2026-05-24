"""
Domain exceptions with automatic HTTP mapping.

All business logic raises these typed exceptions.
The global exception handler in main.py converts them to proper HTTP responses.
This keeps business logic clean — services never import FastAPI.
"""
from dataclasses import dataclass, field
from typing import Any


# ── Base ───────────────────────────────────────────────────────────────────────

@dataclass
class TrackBaseException(Exception):
    """Base class for all Track domain exceptions."""
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


# ── 404 Not Found ──────────────────────────────────────────────────────────────

@dataclass
class ResourceNotFoundError(TrackBaseException):
    """Resource does not exist or belongs to a different user."""
    resource_type: str = "Resource"
    resource_id: str = ""

    def __post_init__(self) -> None:
        if not self.message:
            self.message = f"{self.resource_type} '{self.resource_id}' not found"


# ── 409 Conflict ───────────────────────────────────────────────────────────────

@dataclass
class ResourceAlreadyExistsError(TrackBaseException):
    """Resource with this key already exists (e.g., duplicate email)."""
    resource_type: str = "Resource"


# ── 400 Bad Request ────────────────────────────────────────────────────────────

@dataclass
class ValidationError(TrackBaseException):
    """Business rule validation failed (distinct from Pydantic schema validation)."""
    field: str = ""


@dataclass
class InvalidOperationError(TrackBaseException):
    """Attempted operation is not valid in the current state."""


# ── 403 Forbidden ──────────────────────────────────────────────────────────────

@dataclass
class PermissionDeniedError(TrackBaseException):
    """User does not have permission to access/modify this resource."""


# ── 401 Unauthorized ───────────────────────────────────────────────────────────

@dataclass
class AuthenticationError(TrackBaseException):
    """Authentication failed or token is invalid/expired."""


# ── 503 Service Unavailable ────────────────────────────────────────────────────

@dataclass
class ExternalServiceError(TrackBaseException):
    """External service (OpenAI, USDA, etc.) is unavailable or returned an error."""
    service: str = "external"
    retryable: bool = True


# ── 422 Estimation Errors ──────────────────────────────────────────────────────

@dataclass
class CalorieEstimationError(TrackBaseException):
    """The calorie estimation pipeline failed to produce a result."""
    estimation_stage: str = ""  # memory, dataset, llm, scoring


# ── HTTP Status Mapping ────────────────────────────────────────────────────────

EXCEPTION_STATUS_CODES: dict[type, int] = {
    ResourceNotFoundError: 404,
    ResourceAlreadyExistsError: 409,
    ValidationError: 400,
    InvalidOperationError: 400,
    PermissionDeniedError: 403,
    AuthenticationError: 401,
    ExternalServiceError: 503,
    CalorieEstimationError: 422,
}


def get_http_status(exc: TrackBaseException) -> int:
    """Map a domain exception to its HTTP status code."""
    return EXCEPTION_STATUS_CODES.get(type(exc), 500)
