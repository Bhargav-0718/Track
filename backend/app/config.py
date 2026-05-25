"""
Application configuration using Pydantic Settings.
All values read from environment variables or .env file.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "Track Fitness API"
    environment: Literal["development", "staging", "production", "testing"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    secret_key: str = Field(min_length=32)
    api_v1_prefix: str = "/api/v1"

    # ── Database (MongoDB) ─────────────────────────────────────────────────────
    mongodb_url: str
    mongodb_db_name: str = "track_db"

    # ── OpenAI ─────────────────────────────────────────────────────────────────
    openai_api_key: str
    openai_chat_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    openai_max_retries: int = 3
    openai_timeout_seconds: int = 30

    # ── Nutrition Database ─────────────────────────────────────────────────────
    nutrition_db_min_similarity: float = 0.15
    nutrition_db_high_confidence_threshold: float = 0.45

    # ── Estimation Pipeline ────────────────────────────────────────────────────
    memory_high_confidence_threshold: float = 0.85
    memory_low_confidence_threshold: float = 0.60

    # ── JWT ─────────────────────────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # ── Storage (Phase 3) ──────────────────────────────────────────────────────
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: str = "uploads"
    storage_max_file_size_mb: int = 20
    storage_allowed_extensions: list[str] = ["jpg", "jpeg", "png", "webp", "heic"]
    storage_public_url_prefix: str = "/uploads"

    # ── Vision (Phase 3) ───────────────────────────────────────────────────────
    vision_max_image_dimension: int = 1024

    # ── CORS ───────────────────────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:8080",
    ]
    cors_allow_credentials: bool = True

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


# Module-level singleton for imports that can't use DI
settings = get_settings()
