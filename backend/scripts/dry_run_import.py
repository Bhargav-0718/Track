"""Quick dry-run of the import script — no DB needed, just validates parsing."""
import csv, sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def slugify(text):
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    return slug[:120]

def parse_float(value):
    if not value or not value.strip(): return None
    try: return float(value.strip())
    except ValueError: return None

csv_path = Path("data/Indian_Food_Nutrition_Processed.csv")
with open(csv_path, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

valid, skipped, missing_cal = 0, 0, 0
calorie_ranges = {"0-50": 0, "50-100": 0, "100-200": 0, "200-400": 0, "400-600": 0, "600+": 0}

for row in rows:
    name = row.get("Dish Name", "").strip()
    cal = parse_float(row.get("Calories (kcal)", ""))
    if not name or cal is None:
        skipped += 1
        if not cal: missing_cal += 1
        continue
    valid += 1
    if cal < 50:    calorie_ranges["0-50"] += 1
    elif cal < 100: calorie_ranges["50-100"] += 1
    elif cal < 200: calorie_ranges["100-200"] += 1
    elif cal < 400: calorie_ranges["200-400"] += 1
    elif cal < 600: calorie_ranges["400-600"] += 1
    else:           calorie_ranges["600+"] += 1

print(f"Dry run complete:")
print(f"  Valid entries ready to import: {valid}")
print(f"  Skipped (invalid): {skipped} | missing calories: {missing_cal}")
print(f"  Calorie distribution (per 100g):")
for k, v in calorie_ranges.items():
    bar = '#' * (v // 5)
    print(f"    {k:>8} kcal: {bar} ({v})")

# Test some key lookups
print(f"\nSample: high-calorie fried foods (>600 kcal/100g):")
with open(csv_path, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        cal = parse_float(row.get("Calories (kcal)", ""))
        if cal and cal > 600:
            print(f"  {row['Dish Name']}: {cal:.0f} kcal/100g")

print(f"\nSample: common Indian daily foods:")
targets = ["Chapati/Roti", "Dal", "Rice", "Butter chicken", "Paneer", "Samosa"]
with open(csv_path, encoding="utf-8") as f:
    all_rows = list(csv.DictReader(f))
for t in targets:
    matches = [r for r in all_rows if t.lower() in r['Dish Name'].lower()][:1]
    for m in matches:
        print(f"  {m['Dish Name']}: {m['Calories (kcal)']} kcal | P:{m['Protein (g)']}g C:{m['Carbohydrates (g)']}g F:{m['Fats (g)']}g")

print(f"\n✓ Import script will insert {valid} INDB dishes into nutrition_cache.")
