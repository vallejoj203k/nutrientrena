"""
Import foods from USDA FoodData Central + translate names with DeepL.
Outputs a SQL file (aliments_usda.sql) ready to import into Railway.

Setup:
  pip install requests deepl python-dotenv

Usage:
  python scripts/import_usda.py

Get free API keys:
  USDA  → https://fdc.nal.usda.gov/api-guide.html
  DeepL → https://www.deepl.com/pro-api  (plan Free: 500k chars/month)
"""

import os
import sys
import time
import uuid
import requests
import deepl
from dotenv import load_dotenv

load_dotenv()

USDA_API_KEY  = os.environ.get("USDA_API_KEY", "")
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "")

if not USDA_API_KEY:
    sys.exit("❌  Falta USDA_API_KEY en .env")
if not DEEPL_API_KEY:
    sys.exit("❌  Falta DEEPL_API_KEY en .env")

MAX_FOODS  = 15_000
DATA_TYPES = ["Foundation", "SR Legacy"]
OUTPUT_SQL = "scripts/aliments_usda.sql"

CATEGORY_MAP: dict[str, str] = {
    "Dairy and Egg Products":               "Lácteos y huevos",
    "Spices and Herbs":                     "Especias y hierbas",
    "Fats and Oils":                        "Grasas y aceites",
    "Poultry Products":                     "Aves",
    "Soups, Sauces, and Gravies":           "Salsas y sopas",
    "Sausages and Luncheon Meats":          "Embutidos",
    "Breakfast Cereals":                    "Cereales de desayuno",
    "Fruits and Fruit Juices":              "Frutas",
    "Pork Products":                        "Cerdo",
    "Vegetables and Vegetable Products":    "Verduras y vegetales",
    "Nut and Seed Products":                "Frutos secos y semillas",
    "Beef Products":                        "Res y vacuno",
    "Beverages":                            "Bebidas",
    "Finfish and Shellfish Products":       "Pescados y mariscos",
    "Legumes and Legume Products":          "Legumbres",
    "Lamb, Veal, and Game Products":        "Cordero y caza",
    "Baked Products":                       "Panadería y repostería",
    "Sweets":                               "Dulces",
    "Cereal Grains and Pasta":              "Granos y pastas",
    "Fast Foods":                           "Comida rápida",
    "Snacks":                               "Snacks",
    "Meals, Entrees, and Side Dishes":      "Platos preparados",
    "Restaurant Foods":                     "Restaurantes",
    "Ethnic Foods":                         "Cocina étnica",
    "American Indian/Alaska Native Foods":  "Otros",
    "Baby Foods":                           "Alimentos infantiles",
}

NUT_PROTEIN = 1003
NUT_FAT     = 1004
NUT_CARBS   = 1005
NUT_KCAL    = 1008


def get_nutrient(food: dict, nutrient_id: int) -> float | None:
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId") or n.get("nutrient", {}).get("id")
        if nid == nutrient_id:
            val = n.get("value") or n.get("amount") or 0
            return round(float(val), 2)
    return None


def fetch_usda_page(page: int, page_size: int = 200) -> list[dict]:
    r = requests.get(
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={
            "api_key":    USDA_API_KEY,
            "query":      "",
            "dataType":   DATA_TYPES,
            "pageSize":   page_size,
            "pageNumber": page,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("foods", [])


def translate_batch(translator: deepl.Translator, names: list[str]) -> list[str]:
    if not names:
        return []
    try:
        results = translator.translate_text(names, target_lang="ES", source_lang="EN")
        return [r.text for r in results]
    except Exception as e:
        print(f"  ⚠️  DeepL error: {e} — usando nombres en inglés")
        return names


def sql_escape(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, str):
        return "'" + val.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return str(val)


def main():
    translator = deepl.Translator(DEEPL_API_KEY)

    # Collect all unique group names first, assign sequential IDs
    group_counter = 1
    group_id_map: dict[str, int] = {}

    print(f"🚀  Descargando hasta {MAX_FOODS:,} alimentos de USDA...\n")

    # ── Pass 1: fetch all pages and store raw data ─────────────────────────────
    all_foods: list[dict] = []
    page = 1
    while len(all_foods) < MAX_FOODS:
        try:
            foods = fetch_usda_page(page)
        except Exception as e:
            print(f"  ⚠️  Error página {page}: {e}")
            break
        if not foods:
            print("   No hay más páginas.")
            break
        all_foods.extend(foods)
        print(f"   Página {page}: {len(all_foods):,} alimentos descargados")
        page += 1
        time.sleep(0.3)

    all_foods = all_foods[:MAX_FOODS]
    print(f"\n✅  Total descargado: {len(all_foods):,} alimentos\n")

    # Collect groups
    for food in all_foods:
        cat_en = food.get("foodCategory") or food.get("foodCategoryLabel") or ""
        group_name = CATEGORY_MAP.get(cat_en, "Otros")
        if group_name not in group_id_map:
            group_id_map[group_name] = group_counter
            group_counter += 1

    # ── Pass 2: translate names in batches ────────────────────────────────────
    print("🌐  Traduciendo nombres al español con DeepL...\n")
    batch_size = 50
    en_names = [f.get("description", "Unknown") for f in all_foods]
    es_names: list[str] = []

    for i in range(0, len(en_names), batch_size):
        batch = en_names[i:i + batch_size]
        translated = translate_batch(translator, batch)
        es_names.extend(translated)
        done = min(i + batch_size, len(en_names))
        print(f"   Traducidos {done:,} / {len(en_names):,}")
        time.sleep(0.1)

    # ── Pass 3: write SQL file ─────────────────────────────────────────────────
    print(f"\n📝  Generando {OUTPUT_SQL}...\n")

    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write("-- USDA FoodData Central import — generado automáticamente\n")
        f.write("-- Ejecutar en Railway: railway run mysql < scripts/aliments_usda.sql\n\n")
        f.write("SET NAMES utf8mb4;\n\n")

        # Groups
        f.write("-- ── Grupos de alimentos ──────────────────────────────────────────\n")
        for name, gid in sorted(group_id_map.items(), key=lambda x: x[1]):
            f.write(
                f"INSERT INTO group_foods (name, status, created_at, updated_at) "
                f"VALUES ({sql_escape(name)}, 1, NOW(), NOW()) "
                f"ON DUPLICATE KEY UPDATE name=name;\n"
            )
        f.write("\n")

        # Aliments
        f.write("-- ── Alimentos ───────────────────────────────────────────────────\n")
        for food, es_name in zip(all_foods, es_names):
            cat_en     = food.get("foodCategory") or food.get("foodCategoryLabel") or ""
            group_name = CATEGORY_MAP.get(cat_en, "Otros")
            fdc_id     = food["fdcId"]

            proteins = get_nutrient(food, NUT_PROTEIN)
            fats     = get_nutrient(food, NUT_FAT)
            carbs    = get_nutrient(food, NUT_CARBS)
            kcal     = get_nutrient(food, NUT_KCAL)

            aid = str(uuid.uuid4())
            f.write(
                f"INSERT INTO aliments "
                f"(id, name, group_food_id, proteins, carbohydrates, fats, calories, "
                f"quantity, comments, created_at, updated_at) "
                f"SELECT {sql_escape(aid)}, {sql_escape(es_name[:255])}, "
                f"(SELECT id FROM group_foods WHERE name={sql_escape(group_name)} LIMIT 1), "
                f"{sql_escape(proteins)}, {sql_escape(carbs)}, {sql_escape(fats)}, "
                f"{sql_escape(kcal)}, 100, {sql_escape('usda:' + str(fdc_id))}, NOW(), NOW() "
                f"WHERE NOT EXISTS "
                f"(SELECT 1 FROM aliments WHERE comments={sql_escape('usda:' + str(fdc_id))});\n"
            )

    total_groups = len(group_id_map)
    print(f"🎉  Archivo generado: {OUTPUT_SQL}")
    print(f"    {len(all_foods):,} alimentos · {total_groups} grupos\n")
    print("─" * 60)
    print("Próximo paso — ejecutar en tu terminal local:")
    print(f"  railway run mysql railway < {OUTPUT_SQL}")
    print("─" * 60)


if __name__ == "__main__":
    main()
