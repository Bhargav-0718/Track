"""
Embedding service using text-embedding-3-small.

Used for:
1. Embedding food_memory entries (on creation and update)
2. Embedding user query (before similarity search)

Cost: $0.02 / 1M tokens — effectively free at personal scale.
A typical food name is 5-15 tokens → ~$0.0000003 per embedding.
"""
from app.config import settings
from app.core.logging import get_logger
from app.services.ai.client import get_openai_client

logger = get_logger(__name__)


async def embed_text(text: str) -> list[float]:
    """
    Generate a 1536-dimension embedding for a text string.

    The text is normalized before embedding to improve similarity matching:
    - Lowercased
    - Extra whitespace removed
    - Common synonyms expanded (e.g., "atta" → "whole wheat flour")
    """
    normalized = _normalize_food_text(text)

    client = get_openai_client()
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=normalized,
        dimensions=settings.openai_embedding_dimensions,
    )

    embedding = response.data[0].embedding
    logger.debug("embedding_generated", text=text[:50], dimensions=len(embedding))
    return embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in a single API call.
    More efficient for bulk operations (dataset seeding, etc.).
    Max batch size: 2048 inputs.
    """
    if not texts:
        return []

    normalized = [_normalize_food_text(t) for t in texts]
    client = get_openai_client()

    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=normalized,
        dimensions=settings.openai_embedding_dimensions,
    )

    # Response data is ordered same as input
    embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
    logger.info("batch_embeddings_generated", count=len(embeddings))
    return embeddings


def _normalize_food_text(text: str) -> str:
    """
    Normalize food text before embedding for better similarity matching.

    Why this matters: "dal chawal" and "dal rice" should be near-identical
    in embedding space. Without normalization, regional naming variations
    would reduce similarity scores.
    """
    normalized = text.lower().strip()

    # Common Indian food term synonyms (expand to improve similarity)
    synonyms = {
        "atta": "whole wheat flour chapati",
        "chawal": "rice",
        "dal": "lentil",
        "daal": "lentil",
        "sabzi": "vegetable curry",
        "sabji": "vegetable curry",
        "bhaji": "vegetable",
        "anda": "egg",
        "murgi": "chicken",
        "murg": "chicken",
        "gosht": "mutton",
        "machli": "fish",
        "paneer": "cottage cheese",
        "dahi": "yogurt curd",
        "lassi": "yogurt drink",
        "chai": "tea",
        "pani": "water",
        "ghee": "clarified butter",
        "maida": "refined flour",
        "besan": "gram flour chickpea flour",
        "rajma": "kidney beans",
        "chana": "chickpea",
        "matar": "peas",
        "aloo": "potato",
        "tamatar": "tomato",
        "pyaaz": "onion",
        "adrak": "ginger",
        "lehsun": "garlic",
    }

    for hindi_term, english_term in synonyms.items():
        if hindi_term in normalized:
            normalized = normalized + " " + english_term

    return normalized
