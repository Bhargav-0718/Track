"""
FastAPI application factory.

Lifecycle:
1. configure_logging() — structlog setup
2. FastAPI app created with metadata
3. CORS middleware added
4. Request ID middleware added (for log correlation)
5. Global exception handlers registered
6. API router mounted at /api/v1

Startup/shutdown hooks handle:
- MongoDB init via Beanie (registers all document models)
- Database connectivity check
- Clean disconnect on shutdown
"""
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import TrackBaseException, get_http_status
from app.core.logging import configure_logging, get_logger
from app.database import check_database_connection, close_db, init_db
from app.schemas.common import ErrorResponse, HealthResponse

# Configure logging before anything else
configure_logging()
logger = get_logger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown logic."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info(
        "track_api_starting",
        environment=settings.environment,
        version="0.1.0",
    )

    # Initialize MongoDB + Beanie (registers all Document models)
    await init_db()

    logger.info("mongodb_connected", db=settings.mongodb_db_name)
    logger.info("track_api_ready", prefix=settings.api_v1_prefix)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("track_api_shutting_down")
    await close_db()


# ── App Factory ────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="""
## Track — Adaptive AI Fitness Memory System

An adaptive fitness memory system that becomes smarter and more personalized over time.

### Key Features
- **Fast food logging** with natural language input
- **Adaptive calorie estimation** with confidence scoring
- **Semantic memory** that learns your food preferences
- **Workout tracking** with MET-based calorie estimation
- **Health Connect integration** for Android activity data
- **Progress insights** with behavioral learning

### API Versioning
All endpoints are versioned under `/api/v1/`.
        """,
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: ...) -> Response:
        """
        Add a unique request ID to every request.
        Enables log correlation across distributed traces.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=request_id,
        )

        return response

    # ── Exception Handlers ─────────────────────────────────────────────────────

    @app.exception_handler(TrackBaseException)
    async def domain_exception_handler(
        request: Request,
        exc: TrackBaseException,
    ) -> JSONResponse:
        """Convert domain exceptions to structured HTTP responses."""
        http_status = get_http_status(exc)
        request_id = getattr(request.state, "request_id", None)

        logger.warning(
            "domain_exception",
            exception_type=type(exc).__name__,
            message=exc.message,
            status_code=http_status,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=http_status,
            content=ErrorResponse(
                error=type(exc).__name__,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch-all for unhandled exceptions — log and return 500."""
        request_id = getattr(request.state, "request_id", None)

        logger.error(
            "unhandled_exception",
            exception_type=type(exc).__name__,
            message=str(exc),
            request_id=request_id,
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="InternalServerError",
                message="An unexpected error occurred",
                request_id=request_id,
            ).model_dump(),
        )

    # ── Static Files (local photo serving) ────────────────────────────────────
    # Serves uploaded progress photos at /uploads/{user_id}/{year}/{month}/{file}
    # In production, replace with a CDN or S3 presigned URLs.
    import os
    uploads_root = settings.storage_local_root
    os.makedirs(uploads_root, exist_ok=True)
    app.mount(
        settings.storage_public_url_prefix,
        StaticFiles(directory=uploads_root),
        name="uploads",
    )

    # ── Routes ─────────────────────────────────────────────────────────────────

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Health check",
    )
    async def health_check() -> HealthResponse:
        """
        Health check endpoint for Docker/load balancer health probes.
        Returns database connectivity status.
        """
        from datetime import datetime, timezone
        db_ok = await check_database_connection()
        return HealthResponse(
            status="healthy" if db_ok else "degraded",
            database=db_ok,
            version="0.1.0",
            environment=settings.environment,
            timestamp=datetime.now(timezone.utc),
        )

    @app.get("/", tags=["system"])
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
