"""
Indian Portion Vocabulary — the single source of truth for portion → grams mapping.

This module converts natural language Indian portion descriptions into gram estimates.
These estimates are used to scale per-100g nutrition values to actual consumed quantities.

Sources:
- ICMR-NIN standard household measures
- Common Indian kitchen measurements
- Validated against INDB serving size data

All values are approximate. User corrections feed back into food_memory to
personalize these defaults over time (Phase 4).
"""
from dataclasses import dataclass


@dataclass
class PortionMatch:
    estimated_grams: float
    description: str        # Human-readable: "1 medium katori ≈ 150g"
    confidence: float       # 0-1, how confident we are in this estimate


# ── Katori / Bowl Sizes ────────────────────────────────────────────────────────
# Katori: standard Indian bowl, used for dal, sabzi, curry, rice, desserts
# Typical katori volume: small=100ml, medium=150ml, large=200ml
# For liquids/semi-liquids: 1ml ≈ 1g
# For solids (rice, dal): density factor applied

KATORI_SIZES: dict[str, float] = {
    "mini":   80.0,
    "small":  100.0,
    "medium": 150.0,
    "normal": 150.0,
    "standard": 150.0,
    "large":  200.0,
    "big":    200.0,
    "full":   250.0,
    "vati":   100.0,   # Gujarati/Marathi term for small katori
    "katora": 150.0,   # Alternate spelling
}

# ── Piece Counts — Common Indian Items ────────────────────────────────────────
# Validated against INDB recipe weights (grams per standard piece)

PIECE_WEIGHTS: dict[str, float] = {
    # Breads (homemade Indian standard — verified against ICMR-NIN household measures)
    "roti":           30.0,   # 1 thin homemade roti ≈ 25-30g
    "chapati":        30.0,
    "chapathi":       30.0,
    "chappati":       30.0,
    "fulka":          25.0,   # thinner than roti
    "phulka":         25.0,
    "paratha":        75.0,
    "parantha":       75.0,
    "naan":          100.0,
    "puri":           25.0,
    "poori":          25.0,
    "bhatura":        90.0,
    "thepla":         35.0,
    "litti":          60.0,
    "kulcha":         80.0,
    "rumali":         50.0,
    # Bhakri family — thick, denser than roti
    "bhakri":         55.0,   # 1 medium bhakri ≈ 50-60g
    "jowar bhakri":   55.0,
    "bajra bhakri":   55.0,
    "nachni bhakri":  55.0,
    "makki roti":     45.0,

    # South Indian
    "idli":       45.0,
    "dosa":      100.0,
    "uttapam":   120.0,
    "appam":      60.0,
    "vada":       40.0,
    "medu vada":  40.0,

    # Snacks / Street Food
    "samosa":     75.0,
    "pakora":     20.0,
    "pakoda":     20.0,
    "kachori":    60.0,
    "aloo tikki": 75.0,
    "tikki":      75.0,
    "vada pav":  130.0,  # bun + vada
    "pav":        50.0,
    "sandwich":  130.0,
    "toast":      30.0,

    # Sweets / Desserts
    "ladoo":      40.0,
    "laddoo":     40.0,
    "barfi":      30.0,
    "burfi":      30.0,
    "gulab jamun": 35.0,
    "jalebi":     25.0,
    "kheer":     150.0,  # standard serving
    "halwa":     100.0,
    "rasgulla":   30.0,

    # Eggs
    "egg":        55.0,
    "anda":       55.0,

    # Fruits
    "banana":     90.0,    # medium, peeled
    "apple":     150.0,    # medium
    "orange":    130.0,    # medium, peeled
    "mango":     200.0,    # medium slice/portion
}

# ── Plate / Thali Sizes ───────────────────────────────────────────────────────
# Plate descriptions for rice dishes, full meals

PLATE_SIZES: dict[str, float] = {
    "quarter plate": 100.0,
    "half plate":    200.0,
    "full plate":    350.0,
    "large plate":   450.0,
    "small plate":   150.0,
    "thali":         500.0,   # Full thali is very variable
    "mini thali":    300.0,
}

# ── Glass / Cup Sizes ─────────────────────────────────────────────────────────

GLASS_SIZES: dict[str, float] = {
    "small glass":   150.0,
    "medium glass":  200.0,
    "large glass":   300.0,
    "glass":         200.0,
    "cup":           200.0,
    "mug":           300.0,
    "tea cup":       150.0,
    "small cup":     100.0,
    "large cup":     250.0,
}

# ── Spoon Measures ────────────────────────────────────────────────────────────

SPOON_SIZES: dict[str, float] = {
    "tsp":   5.0,
    "tbsp":  15.0,
    "teaspoon":    5.0,
    "tablespoon":  15.0,
    "teaspoons":   5.0,
    "tablespoons": 15.0,
}

# ── LLM Prompt Context ────────────────────────────────────────────────────────
# This string is injected into the LLM system prompt to ground portion estimates.

PORTION_CONTEXT = """
INDIAN PORTION VOCABULARY (use these as reference for gram estimates):

Katori/Bowl sizes (grams):
- 1 small katori = 100g
- 1 medium katori = 150g
- 1 large katori = 200g
- 1 vati (Gujarati small bowl) = 100g
- 1 full bowl = 250g

Common Indian bread/item piece weights (homemade standard):
- 1 roti/chapati/fulka = 30g   ← thin homemade roti, NOT restaurant size
- 1 bhakri (jowar/bajra/nachni) = 55g  ← thick flatbread, heavier than roti
- 1 paratha = 75g
- 1 naan = 100g
- 1 puri/poori = 25g
- 1 bhatura = 90g
- 1 idli = 45g
- 1 dosa = 100g
- 1 vada = 40g
- 1 samosa = 75g
- 1 pakora/pakoda = 20g
- 1 egg/anda = 55g

Plate sizes:
- half plate = 200g
- full plate = 350g
- thali = 500g (highly variable)

Cups/glasses:
- 1 cup = 200ml ≈ 200g for liquids
- 1 glass = 200ml ≈ 200g for liquids
- 1 tea cup = 150ml

Spoons:
- 1 tsp = 5g
- 1 tbsp = 15g

For compound portion descriptions like "2 roti and 1 katori dal":
- Treat as a single meal entry with combined grams
- Return the primary food item as the main entry

IMPORTANT: These are estimates. If the user corrects them, that correction is stored and
used for future estimates. Do not pretend to be more precise than ±20%.
"""


def estimate_grams_from_description(description: str) -> PortionMatch | None:
    """
    Try to estimate grams from a portion description using the lookup tables.
    Returns None if no match found — LLM will handle it.

    Examples:
        "medium katori" → PortionMatch(150.0, "1 medium katori ≈ 150g", 0.7)
        "2 roti" → PortionMatch(70.0, "2 rotis ≈ 70g", 0.75)
        "half plate" → PortionMatch(200.0, "half plate ≈ 200g", 0.6)
    """
    desc = description.lower().strip()

    # Try to extract count (e.g., "2 roti", "3 idli")
    count = 1.0
    import re
    count_match = re.match(r'^(\d+(?:\.\d+)?)\s+(.+)$', desc)
    if count_match:
        count = float(count_match.group(1))
        desc = count_match.group(2).strip()

    # Try piece weights first
    for item, grams in PIECE_WEIGHTS.items():
        if item in desc or desc.rstrip('s') == item:  # handle plurals ("rotis")
            total = grams * count
            return PortionMatch(
                estimated_grams=total,
                description=f"{count:.0f} {item} ≈ {total:.0f}g",
                confidence=0.75,
            )

    # Try katori with size modifier
    for size, grams in KATORI_SIZES.items():
        if size in desc and ('katori' in desc or 'bowl' in desc or 'vati' in desc):
            return PortionMatch(
                estimated_grams=grams * count,
                description=f"{count:.0f} {size} katori ≈ {grams * count:.0f}g",
                confidence=0.70,
            )

    # Plain katori/bowl without size
    if any(w in desc for w in ['katori', 'bowl', 'vati', 'katora']):
        grams = KATORI_SIZES["medium"]
        return PortionMatch(
            estimated_grams=grams * count,
            description=f"1 katori (medium assumed) ≈ {grams:.0f}g",
            confidence=0.55,
        )

    # Plate sizes
    for plate, grams in PLATE_SIZES.items():
        if plate in desc:
            return PortionMatch(
                estimated_grams=grams,
                description=f"{plate} ≈ {grams:.0f}g",
                confidence=0.55,
            )

    # Glass/cup sizes
    for glass, grams in GLASS_SIZES.items():
        if glass in desc:
            return PortionMatch(
                estimated_grams=grams * count,
                description=f"{count:.0f} {glass} ≈ {grams * count:.0f}g",
                confidence=0.65,
            )

    # Spoon measures
    for spoon, grams in SPOON_SIZES.items():
        if spoon in desc:
            return PortionMatch(
                estimated_grams=grams * count,
                description=f"{count:.0f} {spoon} ≈ {grams * count:.0f}g",
                confidence=0.8,
            )

    return None  # LLM will handle unknown portions
