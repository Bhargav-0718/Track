"""
OpenAI async client — singleton with retry and timeout configuration.

Shared across embedding_service and llm_service.
Never instantiate AsyncOpenAI directly in services — always use get_openai_client().
"""
from functools import lru_cache

from openai import AsyncOpenAI

from app.config import settings


@lru_cache(maxsize=1)
def get_openai_client() -> AsyncOpenAI:
    """
    Cached OpenAI async client.
    Retry and timeout configured from settings.
    """
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        max_retries=settings.openai_max_retries,
        timeout=settings.openai_timeout_seconds,
    )
