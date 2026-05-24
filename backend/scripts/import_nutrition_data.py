"""
One-time INDB nutrition data importer.

Imports Indian_Food_Nutrition_Processed.csv (1,014 dishes from the Indian
Nutrient Databank) into the nutrition_cache table.

Run once after initial database setup:
    python scripts/import_nutrition_data.py

Safe to re-run — uses INSERT OR SKIP on external_id conflict.
Data source: INDB (Indian Nutrient Databank), open-access, peer-reviewed.
Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11277795/
"""
import asyncio
import csv
import re
import sys
from pathlib import Path

# Make app importable from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.nutrition_cache import NutritionCache


def slugify(text: str) -> str:
    """Convert food name to a stable external_id slug."""
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:120]


def parse_float(value: str) -> float | None:
    """Parse a CSV float value, returning None for empty/invalid."""
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def parse_row(row: dict) -> NutritionCache | None:
    """
    Parse a single CSV row into a NutritionCache model.
    Returns None if the row is invalid (missing required fields).
    """
    dish_name = row.get("Dish Name", "").strip()
    if not dish_name:
        return None

    calories_str = row.get("Calories (kcal)", "")
    calories = parse_float(calories_str)
    if calories is None:
        print(f"  SKIP (no calories): {dish_name}")
        return None

    external_id = slugify(dish_name)

    return NutritionCache(
        source="indb",
        external_id=external_id,
        food_name=dish_name,
        calories_per_100g=calories,
        protein_per_100g=parse_float(row.get("Protein (g)", "")),
        carbs_per_100g=parse_float(row.get("Carbohydrates (g)", "")),
        fat_per_100g=parse_float(row.get("Fats (g)", "")),
        fiber_per_100g=parse_float(row.get("Fibre (g)", "")),
        sodium_per_100g=parse_float(row.get("Sodium (mg)", "")),
        # Store full row in raw_data for future use
        raw_data={
            "free_sugar_g": parse_float(row.get("Free Sugar (g)", "")),
            "calcium_mg": parse_float(row.get("Calcium (mg)", "")),
            "iron_mg": parse_float(row.get("Iron (mg)", "")),
            "vitamin_c_mg": parse_float(row.get("Vitamin C (mg)", "")),
            "folate_ug": parse_float(row.get("Folate (µg)", "")),
            "source_paper": "INDB 2024 - Indian Nutrient Databank",
            "values_per": "100g",
        },
    )


async def import_indb(csv_path: str = "data/Indian_Food_Nutrition_Processed.csv") -> None:
    """Import INDB CSV data into the nutrition_cache table."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"ERROR: File not found: {csv_path}")
        print("Make sure you're running from the backend/ directory.")
        sys.exit(1)

    print(f"Reading {csv_path}...")

    with open(csv_file, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Found {len(rows)} rows to import.")

    inserted = 0
    skipped = 0
    errors = 0

    async with AsyncSessionLocal() as session:
        for i, row in enumerate(rows, 1):
            try:
                entry = parse_row(row)
                if entry is None:
                    skipped += 1
                    continue

                # Check if already exists (safe re-run)
                from sqlalchemy import select
                existing = await session.execute(
                    select(NutritionCache).where(
                        NutritionCache.source == "indb",
                        NutritionCache.external_id == entry.external_id,
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue

                session.add(entry)
                inserted += 1

                # Commit in batches of 50
                if inserted % 50 == 0:
                    await session.commit()
                    print(f"  Committed {inserted} entries...")

            except Exception as e:
                print(f"  ERROR on row {i} ({row.get('Dish Name', '?')}): {e}")
                errors += 1

        # Final commit
        if inserted % 50 != 0:
            await session.commit()

    print()
    print("=" * 50)
    print(f"Import complete!")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (duplicates/invalid): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total processed: {len(rows)}")

    if inserted > 0:
        print()
        print("Next step: Generate trgm index for fast fuzzy search.")
        print("Run: alembic upgrade head")


async def verify_import() -> None:
    """Quick verification that data was imported correctly."""
    from sqlalchemy import func, select
    async with AsyncSessionLocal() as session:
        count_result = await session.execute(
            select(func.count()).select_from(NutritionCache).where(
                NutritionCache.source == "indb"
            )
        )
        count = count_result.scalar_one()

        # Test fuzzy search
        from sqlalchemy import text
        test_result = await session.execute(
            select(NutritionCache).where(
                NutritionCache.source == "indb"
            ).order_by(NutritionCache.food_name).limit(5)
        )
        samples = test_result.scalars().all()

    print(f"\nVerification:")
    print(f"  Total INDB entries in DB: {count}")
    print(f"  Sample entries:")
    for s in samples:
        print(f"    - {s.food_name}: {s.calories_per_100g:.1f} kcal/100g")


if __name__ == "__main__":
    print("Track — INDB Nutrition Data Importer")
    print("=" * 50)

    async def main() -> None:
        await import_indb()
        await verify_import()

    asyncio.run(main())
