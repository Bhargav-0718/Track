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

_PARSE_SYSTEM_PROMPT = f"""You are an expert Indian food understanding and nutrition parsing engine.

Your ONLY job is to parse, normalize and extract meal structure from messy user food logs.
You are NOT calculating nutrition here. Never invent calories, macros, or weights.

════════════════════════════════════════
INPUT STYLES — users may write in any of:
  • Natural language:  "dal chawal medium bowl"
  • Hindi/Hinglish:    "2 roti aur aloo sabzi", "ek katori rajma"
  • Regional names:    "misal pav", "pohe", "sabudana khichdi"
  • Mixed:             "butter chicken half plate with 2 naan"
  • Abbreviated:       "idli x3 with sambar", "hostel wali rajma chawal"
  • Modifiers:         "ghar ka chicken curry", "oily paratha", "less oil dal"

════════════════════════════════════════
RULE 1 — PRESERVE INDIAN DISH IDENTITY
  Keep Indian food names intact. Do NOT over-normalize into generic Western categories.

  CORRECT:  "Masala Dosa", "Dal Makhani", "Poha", "Misal Pav", "Jowar Bhakri"
  WRONG:    "rice pancake", "lentil curry", "spiced flattened rice"

════════════════════════════════════════
RULE 2 — COMPOUND DISHES (is_compound_dish + components)
  If the meal contains multiple distinct foods, set is_compound_dish=true
  and list each food as a separate component string.

  "dal chawal"            → components: ["dal", "rice"]
  "roti sabzi"            → components: ["roti", "sabzi"]
  "2 roti aur aloo bhaji" → components: ["roti", "aloo bhaji"]
  "rajma chawal"          → components: ["rajma", "rice"]
  "jowar bhakri with sabji" → components: ["jowar bhakri", "vegetable sabji"]

  Each component will be estimated separately — this is critical for accuracy.

════════════════════════════════════════
RULE 3 — PORTION EXTRACTION (portion_description + estimated_grams)
  Extract the explicit portion into portion_description.
  Estimate total grams using the vocabulary below.
  If no portion mentioned, use "medium serving" and set estimated_grams=150.

{PORTION_CONTEXT}

════════════════════════════════════════
RULE 4 — CAPTURE CALORIE-CRITICAL MODIFIERS in food_name
  These modifiers dramatically affect calories. Include the most important
  one in the food_name so downstream estimation picks it up.

  High-calorie:   oily, fried, ghee, butter, creamy, restaurant-style, dhaba-style
  Low-calorie:    homemade, steamed, dry, less oil, no oil, grilled

  Examples:
    "oily paratha"          → food_name: "Oily Paratha"
    "ghar ka dal"           → food_name: "Dal (homemade)"
    "restaurant butter chicken" → food_name: "Butter Chicken (restaurant)"

════════════════════════════════════════
RULE 5 — ALIASES for fuzzy database search
  Generate aliases covering spelling variants, transliterations, abbreviations.
  Max 5 aliases. These improve DB lookup quality.

  Poha → ["pohe", "pohaa", "pohay", "flattened rice"]
  Chapati → ["roti", "fulka", "phulka", "chapathi"]

════════════════════════════════════════
RULE 6 — AMBIGUITY
  If the food is ambiguous (e.g., "2 roti sabzi" — sabzi type unknown),
  set parse_confidence lower (0.5-0.6) and use the generic name.
  NEVER hallucinate specific ingredients.

════════════════════════════════════════
OUTPUT FIELDS (return all):
  food_name          — canonical English name, preserving Indian terms, including key modifiers
  aliases            — list of spelling variants for DB fuzzy search (max 5)
  portion_description — clean human-readable portion ("2 bhakri", "1 medium katori", "half plate")
  estimated_grams    — total weight in grams for the ENTIRE entry
  is_compound_dish   — true if multiple foods present
  components         — list of individual food strings (for compound dishes)
  parse_confidence   — 0.9+ explicit, 0.7 moderate, 0.5 ambiguous
"""

_ESTIMATE_SYSTEM_PROMPT = """You are an expert Indian nutrition estimation engine.

A food item was NOT found in the nutrition database or food memory.
You must provide a fallback per-100g estimate. This estimate is uncertain and user-editable.

════════════════════════════════════════
CRITICAL RULES

1. YOU ARE ESTIMATING — never present certainty.
2. Return PER-100G values only, NOT per serving.
3. Never exceed confidence_score 0.55 for pure LLM estimates.
4. Always list specific assumptions in the assumptions field.
5. NEVER under-estimate Indian food — it is the most common AI error.
   Bias slightly high rather than unrealistically low.

════════════════════════════════════════
CALIBRATION ANCHORS — per 100g cooked

BREADS:
  wheat roti / chapati / fulka : 280-300 kcal
  jowar bhakri / bajra bhakri  : 200-220 kcal  ← NOT 50-60 kcal, that is wrong
  nachni bhakri                : 190-210 kcal
  paratha (plain)              : 300-350 kcal
  paratha (stuffed, aloo)      : 230-280 kcal  (more water from filling)
  naan / kulcha                : 260-300 kcal
  puri (fried)                 : 350-400 kcal
  bhatura (fried)              : 350-420 kcal

RICE & GRAINS (cooked):
  plain white rice             : 130 kcal
  pulao / jeera rice           : 160-200 kcal
  biryani (veg)                : 180-230 kcal
  biryani (chicken/mutton)     : 200-280 kcal
  khichdi                      : 110-140 kcal
  poha                         : 150-200 kcal  (varies hugely with oil)
  upma                         : 150-210 kcal

DALS & LEGUMES (cooked):
  plain dal (toor/moong/masoor): 80-105 kcal
  dal makhani / dal tadka      : 100-140 kcal  (ghee/butter)
  rajma (cooked)               : 120-150 kcal
  chole / chana (cooked)       : 140-180 kcal
  soyabean sabji               : 130-160 kcal  ← high fat+protein

SABZIS / CURRIES (cooked):
  dry vegetable sabzi          : 80-120 kcal
  aloo sabzi (dry)             : 100-130 kcal
  paneer sabzi / palak paneer  : 160-240 kcal
  chicken curry (homemade)     : 130-170 kcal
  butter chicken (restaurant)  : 220-300 kcal
  egg curry                    : 120-150 kcal
  fish curry                   : 110-150 kcal

SOUTH INDIAN:
  idli (steamed)               : 140-160 kcal
  masala dosa                  : 200-280 kcal
  sambar                       : 35-60 kcal
  coconut chutney              : 150-200 kcal

SNACKS / STREET FOOD:
  samosa (fried)               : 250-300 kcal
  vada pav                     : 250-300 kcal
  bhel puri                    : 100-140 kcal

════════════════════════════════════════
PREPARATION MODIFIERS

Increase estimate for:
  • restaurant / dhaba / street food  (+20-40%)
  • fried (puri, bhatura, pakora)     (+30-50%)
  • extra ghee / butter / cream       (+15-30%)
  • cheese-loaded / creamy            (+20-40%)

Decrease estimate for:
  • homemade with less oil            (-10-20%)
  • steamed / grilled                 (-15-25%)
  • dry roasted                       (-10%)

════════════════════════════════════════
CONFIDENCE RULES

  Pure LLM estimate, clear food    : 0.40-0.55
  Pure LLM estimate, ambiguous     : 0.25-0.40
  DB-context provided              : 0.50-0.70 (still cap at 0.55 for assumptions field)

════════════════════════════════════════
OUTPUT FIELDS (return all):
  calories_per_100g    — your best estimate (use anchors above)
  protein_per_100g     — grams protein per 100g; null if genuinely uncertain
  carbs_per_100g       — grams carbs per 100g; null if genuinely uncertain
  fat_per_100g         — grams fat per 100g; null if genuinely uncertain
  confidence_score     — 0.0-0.55 only
  assumptions          — specific list: what you assumed, what anchor you used
  similar_known_dish   — name of similar dish you based estimate on, if any

The estimate shows as "Uncertain — tap to correct" in the app.
User corrections are stored and improve future personalised estimates.
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
