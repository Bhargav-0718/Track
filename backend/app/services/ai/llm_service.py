"""
LLM service using GPT-4o mini with structured outputs.

Two jobs:
1. PARSE — always runs. Extracts food name + portion from user's raw text.
2. ESTIMATE — fallback only. Estimates nutrition when DB lookup completely fails.

The LLM is NOT the calorie database. It:
- Interprets natural language input
- Estimates portion sizes
- Provides fallback nutrition with explicit uncertainty flags
- Never claims precision it doesn't have

Structured outputs enforce schema compliance — no hallucinated fields.
"""
from pydantic import BaseModel, Field

from app.config import settings
from app.core.logging import get_logger
from app.core.portions import PORTION_CONTEXT
from app.services.ai.client import get_openai_client

logger = get_logger(__name__)


# ── Structured Output Schemas ──────────────────────────────────────────────────

class FoodParseResult(BaseModel):
    """
    Result of parsing a user's natural language food input.
    Always returned, even for simple inputs.
    """
    food_name: str = Field(
        description="Canonical English food name. E.g. 'Butter Chicken', 'Dal Chawal', 'Masala Dosa'"
    )
    aliases: list[str] = Field(
        description="Alternative names/spellings to try in database lookup. "
                    "E.g. ['butter chicken curry', 'murgh makhani']. Max 5 aliases."
    )
    portion_description: str = Field(
        description="Clean portion description extracted from input. E.g. '1 medium katori', '2 roti'"
    )
    estimated_grams: float = Field(
        description="Estimated weight in grams based on portion description. "
                    "Use the Indian portion vocabulary provided. Be honest — ±20% is fine."
    )
    is_compound_dish: bool = Field(
        description="True if this is a combination meal (e.g., 'dal chawal', 'roti sabzi', 'thali')"
    )
    components: list[str] = Field(
        default_factory=list,
        description="For compound dishes, list the main components. E.g. ['dal', 'rice'] for dal chawal"
    )
    parse_confidence: float = Field(
        description="How confident you are in this parse (0-1). "
                    "High if clear food name and portion. Low if ambiguous input."
    )


class NutritionEstimate(BaseModel):
    """
    LLM fallback nutrition estimate — ONLY used when database lookup completely fails.
    Always includes honest assumptions and uncertainty.
    """
    calories_per_100g: float = Field(
        description="Estimated calories per 100g. This is your best estimate — be honest about range."
    )
    protein_per_100g: float | None = Field(
        default=None,
        description="Estimated protein per 100g in grams. Null if very uncertain."
    )
    carbs_per_100g: float | None = Field(
        default=None,
        description="Estimated carbohydrates per 100g in grams. Null if very uncertain."
    )
    fat_per_100g: float | None = Field(
        default=None,
        description="Estimated fat per 100g in grams. Null if very uncertain."
    )
    confidence_score: float = Field(
        description="Confidence in this estimate (0-1). "
                    "0.3-0.5 for typical LLM estimates without database backing. "
                    "Never claim >0.6 for pure LLM estimates."
    )
    assumptions: list[str] = Field(
        description="List of assumptions made. Be specific. "
                    "E.g. ['Assumed restaurant-style preparation with ~3 tbsp oil', "
                    "'Based on typical North Indian dal recipe', "
                    "'No database match found — estimate only']"
    )
    similar_known_dish: str | None = Field(
        default=None,
        description="Name of a similar dish you based this estimate on, if any."
    )


# ── System Prompts ─────────────────────────────────────────────────────────────

_PARSE_SYSTEM_PROMPT = f"""You are an expert in Indian cuisine and nutrition.
Your job is to parse a user's food log entry and extract structured information.

The user may write in any of these styles:
- Natural language: "dal chawal medium bowl"
- Hindi/regional names: "2 roti aur sabzi", "ek katori rajma"
- Mixed: "butter chicken half plate with 2 naan"
- Abbreviated: "idli x3 with sambar"
- English: "chicken curry with rice, large serving"

{PORTION_CONTEXT}

RULES:
1. Always return a canonical English food name (but keep Indian terms like 'Dal Makhani', 'Masala Dosa')
2. For compound dishes ('dal chawal', 'roti sabzi'), set is_compound_dish=true and list components
3. If no portion is mentioned, assume 'medium serving' (150g for solids, 200ml for liquids)
4. Aliases should help database fuzzy search — include common misspellings and alternate names
5. Do NOT invent nutrition values — that is not your job here
"""

_ESTIMATE_SYSTEM_PROMPT = """You are an expert Indian food nutritionist.
A food item was NOT found in our nutrition database. You must provide a fallback calorie estimate.

CRITICAL RULES:
- You are NOT a nutrition database. You are estimating.
- Never claim confidence > 0.55 for pure estimates.
- Always list your assumptions explicitly.
- Per-100g values only (NOT per serving).
- If you genuinely don't know, say confidence=0.3 and keep the range wide.
- Never provide medical advice or precise health claims.

Your estimate will be shown to the user with an 'Uncertain - tap to correct' badge.
The user's correction will improve future estimates.
"""


# ── Service Functions ──────────────────────────────────────────────────────────

async def parse_food_input(raw_input: str) -> FoodParseResult:
    """
    Parse a user's natural language food log entry into structured data.

    Always called — cheap (small prompt, small output), fast.
    Does NOT estimate nutrition — that's the DB lookup's job.
    """
    client = get_openai_client()

    logger.info("llm_parse_food", input=raw_input[:100])

    response = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this food log entry: {raw_input}"},
        ],
        response_format=FoodParseResult,
        temperature=0.1,   # Low temp for consistent parsing
        max_tokens=500,
    )

    result = response.choices[0].message.parsed
    if result is None:
        # Fallback if parsing fails
        return FoodParseResult(
            food_name=raw_input,
            aliases=[],
            portion_description="medium serving",
            estimated_grams=150.0,
            is_compound_dish=False,
            components=[],
            parse_confidence=0.3,
        )

    logger.info(
        "llm_parse_complete",
        food_name=result.food_name,
        grams=result.estimated_grams,
        confidence=result.parse_confidence,
    )
    return result


async def estimate_nutrition_fallback(
    food_name: str,
    context: str | None = None,
) -> NutritionEstimate:
    """
    Fallback nutrition estimate when database lookup completely fails.

    Only called when BOTH memory lookup AND database lookup fail.
    Result is stored with confidence_level='uncertain'.

    context: Optional context from database (e.g., "Similar dish found: X = 150 kcal/100g")
    """
    client = get_openai_client()

    user_message = f"Estimate nutrition per 100g for: {food_name}"
    if context:
        user_message += f"\n\nContext from our database: {context}"

    logger.info("llm_estimate_fallback", food_name=food_name)

    response = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _ESTIMATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format=NutritionEstimate,
        temperature=0.2,
        max_tokens=400,
    )

    result = response.choices[0].message.parsed
    if result is None:
        # Hard fallback — truly unknown food
        return NutritionEstimate(
            calories_per_100g=200.0,
            confidence_score=0.2,
            assumptions=[
                "Could not parse food name",
                "Used average Indian dish calorie estimate",
                "Please correct manually",
            ],
        )

    # Enforce our own confidence ceiling on LLM estimates
    result.confidence_score = min(result.confidence_score, 0.55)
    result.assumptions.append("No database match found — LLM estimate only")

    logger.info(
        "llm_estimate_complete",
        food_name=food_name,
        calories=result.calories_per_100g,
        confidence=result.confidence_score,
    )
    return result
