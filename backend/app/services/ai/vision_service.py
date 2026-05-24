"""
VisionService — AI-powered physique comparison using GPT-4o multimodal.

Sends two progress photos (before + after) to GPT-4o and receives a
structured comparison covering visible physique changes.

STRICT SAFETY RULES enforced in the prompt:
  ✓ Observable physique observations only (fat distribution, muscle definition, posture)
  ✓ Professional, supportive tone
  ✓ Explicit uncertainty acknowledgment
  ✗ NO medical diagnoses
  ✗ NO health condition claims
  ✗ NO extreme intervention recommendations
  ✗ NO calorie prescription

Image pipeline:
  1. Pillow resizes to max 1024px (config: vision_max_image_dimension)
  2. Converts to JPEG at quality=85 (good balance: ~200-400KB per photo)
  3. Base64 encodes for GPT-4o API
  4. Both images sent in a single API call with structured output schema
"""
import base64
import io
from datetime import date
from typing import Literal

from PIL import Image
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.services.ai.client import get_openai_client

logger = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

VISION_MODEL = "gpt-4o"            # Full model required for image understanding
MAX_IMAGE_DIMENSION = 1024          # px — keeps tokens and costs reasonable
JPEG_QUALITY = 85                   # Compression quality (85 = good quality, small size)
MAX_FILE_SIZE_MB = 20               # Reject images above this size before processing
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP"}

# ── Safety-constrained system prompt ──────────────────────────────────────────

_SYSTEM_PROMPT = """
You are a professional physique assessment assistant for a personal fitness tracking app.
Your role is to provide objective, encouraging observations about visible physical changes
between two progress photos taken at different points in time.

ABSOLUTE RULES — never violate these:
• Observe ONLY what is visually apparent: fat distribution patterns, muscle definition,
  body proportions, posture, and overall physique silhouette
• Use professional, supportive, non-judgmental language at all times
• Never provide medical diagnoses, health assessments, or clinical observations
• Never claim to detect health conditions, diseases, or injuries
• Never prescribe specific diets, calorie targets, or extreme interventions
• Acknowledge the inherent limitations of visual assessment (lighting, angle, clothing)
• Be encouraging regardless of the direction of change — all progress is progress

Think of yourself as a knowledgeable, empathetic personal trainer, not a doctor.
Your observations help users notice changes they might miss in day-to-day life.
""".strip()

_USER_PROMPT_TEMPLATE = """
I'm comparing two progress photos from a fitness journey.

BEFORE photo: taken on {before_date}
AFTER photo: taken on {after_date}
Time elapsed: {days_elapsed} days

The FIRST image is the BEFORE photo.
The SECOND image is the AFTER photo.

Provide a structured physique comparison. Be specific about what you observe,
but always acknowledge that visual assessment has limitations (lighting, angle,
pose differences, clothing). Use an encouraging, professional tone throughout.

Focus on these areas where visible changes are most common:
1. Overall physique silhouette and body composition
2. Midsection and waistline
3. Visible muscle definition (shoulders, arms, legs if visible)
4. Posture and how the person carries themselves
5. Consistency observations (does this look like sustainable progress?)

Remember: observations only — no medical claims, no extreme advice.
""".strip()


# ── Structured Output Schema ───────────────────────────────────────────────────

class _PhysiqueObservation(BaseModel):
    category: Literal[
        "overall", "fat_distribution", "muscle_definition",
        "posture", "waistline", "consistency"
    ]
    observation: str    # 1-3 sentences, specific and professional
    direction: Literal["positive", "neutral", "insufficient_data"]


class _PhysiqueComparisonOutput(BaseModel):
    """
    Structured output from GPT-4o physique comparison.
    Validated by the OpenAI structured outputs API.
    """
    overall_summary: str           # 2-3 sentence overview of visible changes
    observations: list[_PhysiqueObservation]   # Per-category observations
    encouragement: str             # Positive motivational closing (1-2 sentences)
    confidence_note: str           # Caveat about visual assessment limitations
    overall_progress: Literal[
        "significant_progress", "steady_progress",
        "maintenance", "insufficient_data"
    ]


# ── Image Processing ───────────────────────────────────────────────────────────

def preprocess_image(image_bytes: bytes) -> tuple[bytes, int, int]:
    """
    Resize and compress an image for vision API submission.

    Returns:
        (jpeg_bytes, width_px, height_px) of the processed image.

    Raises:
        ValueError if the image format is not supported.
    """
    img = Image.open(io.BytesIO(image_bytes))

    if img.format not in ALLOWED_FORMATS and img.format is not None:
        raise ValueError(
            f"Unsupported image format: {img.format}. "
            f"Allowed: {', '.join(ALLOWED_FORMATS)}"
        )

    # Convert RGBA/P/CMYK → RGB (JPEG doesn't support alpha)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Resize to fit within MAX_IMAGE_DIMENSION × MAX_IMAGE_DIMENSION
    max_dim = settings.vision_max_image_dimension
    if img.width > max_dim or img.height > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # Encode as JPEG
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    jpeg_bytes = output.getvalue()

    logger.debug(
        "image_preprocessed",
        original_size=len(image_bytes),
        processed_size=len(jpeg_bytes),
        width=img.width,
        height=img.height,
    )

    return jpeg_bytes, img.width, img.height


def validate_image(image_bytes: bytes) -> None:
    """
    Validate raw image bytes before processing.

    Raises:
        ValueError if the image is invalid or too large.
    """
    max_bytes = settings.storage_max_file_size_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise ValueError(
            f"Image too large: {len(image_bytes) / 1_048_576:.1f}MB. "
            f"Maximum allowed: {settings.storage_max_file_size_mb}MB"
        )

    # Try to open — raises if corrupt/invalid
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception as e:
        raise ValueError(f"Invalid image file: {e}") from e


def _to_base64_url(jpeg_bytes: bytes) -> str:
    """Encode JPEG bytes as a base64 data URL for GPT-4o."""
    b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


# ── Vision Service ─────────────────────────────────────────────────────────────

async def compare_physique(
    before_image_bytes: bytes,
    after_image_bytes: bytes,
    before_date: date,
    after_date: date,
) -> _PhysiqueComparisonOutput:
    """
    Send before/after photos to GPT-4o and receive structured physique comparison.

    Both images are preprocessed (resized + compressed) before sending.
    Uses OpenAI structured outputs to guarantee a valid response schema.

    Args:
        before_image_bytes: Raw bytes of the before photo
        after_image_bytes:  Raw bytes of the after photo
        before_date:        Date of the before checkpoint
        after_date:         Date of the after checkpoint

    Returns:
        _PhysiqueComparisonOutput with structured observations

    Raises:
        ExternalServiceError if the API call fails
        ValueError if images are invalid
    """
    # Preprocess both images
    before_jpeg, _, _ = preprocess_image(before_image_bytes)
    after_jpeg, _, _ = preprocess_image(after_image_bytes)

    days_elapsed = (after_date - before_date).days
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        before_date=before_date.strftime("%B %d, %Y"),
        after_date=after_date.strftime("%B %d, %Y"),
        days_elapsed=days_elapsed,
    )

    client = get_openai_client()

    logger.info(
        "physique_comparison_started",
        before_date=str(before_date),
        after_date=str(after_date),
        days_elapsed=days_elapsed,
        before_size_kb=round(len(before_jpeg) / 1024),
        after_size_kb=round(len(after_jpeg) / 1024),
    )

    try:
        response = await client.beta.chat.completions.parse(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": _to_base64_url(before_jpeg),
                                "detail": "high",
                            },
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": _to_base64_url(after_jpeg),
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            response_format=_PhysiqueComparisonOutput,
            temperature=0.3,    # Low temperature for consistent, professional output
            max_tokens=1500,
        )
    except Exception as e:
        logger.error("physique_comparison_api_error", error=str(e))
        raise ExternalServiceError(
            message="Physique comparison service temporarily unavailable",
            service="openai_vision",
        ) from e

    result = response.choices[0].message.parsed
    if result is None:
        raise ExternalServiceError(
            message="AI returned an empty response for physique comparison",
            service="openai_vision",
        )

    logger.info(
        "physique_comparison_complete",
        overall_progress=result.overall_progress,
        observation_count=len(result.observations),
        tokens_used=response.usage.total_tokens if response.usage else 0,
    )

    return result
