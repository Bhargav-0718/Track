import csv

# === Indian_Food_Nutrition_Processed.csv ===
with open('data/Indian_Food_Nutrition_Processed.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print('=== Indian_Food_Nutrition_Processed.csv ===')
print(f'Total dishes: {len(rows)}')
print(f'Columns: {list(rows[0].keys())}')
empty_calories = sum(1 for r in rows if not r['Calories (kcal)'].strip())
print(f'Rows with missing calories: {empty_calories}')

cals = [float(r['Calories (kcal)']) for r in rows if r['Calories (kcal)'].strip()]
print(f'Calorie range: {min(cals):.1f} to {max(cals):.1f}')
print(f'Average: {sum(cals)/len(cals):.1f}')

print('\nKey dish lookups:')
targets = ['biryani','dal ','roti','idli','dosa','paneer','butter chicken','samosa','poha','upma','rajma','chole','pav bhaji','khichdi','sabzi','curry','rice','bread','naan','paratha']
for t in targets:
    matches = [r for r in rows if t.lower() in r['Dish Name'].lower()][:2]
    for m in matches:
        print(f"  '{m['Dish Name']}' => {m['Calories (kcal)']} kcal | protein={m['Protein (g)']}g | carbs={m['Carbohydrates (g)']}g | fat={m['Fats (g)']}g")

# === Indian_Food_DF.csv ===
print('\n\n=== Indian_Food_DF.csv ===')
with open('data/Indian_Food_DF.csv', encoding='utf-8') as f:
    content = f.read()

# Count actual distinct food items (not sub-rows due to multiline)
lines = content.split('\n')
print(f'Total lines: {len(lines)}')
# Check how many lines have kj in them (energy rows)
energy_lines = [l for l in lines if 'kcal' in l.lower()]
print(f'Lines containing kcal: {len(energy_lines)}')
print(f'Sample energy lines:')
for l in energy_lines[:5]:
    print(f'  {l[:80]}')

print('\nConclusion: Indian_Food_DF.csv has multiline rows (energy split across lines)')
print('Data quality: Very low. Recommend SKIPPING this file.')
