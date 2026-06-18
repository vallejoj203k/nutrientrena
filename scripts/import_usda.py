"""
Import foods from USDA FoodData Central + translate names with DeepL.

Setup:
  pip install requests deepl sqlalchemy pymysql python-dotenv

Usage:
  python scripts/import_usda.py

Get free API keys:
  USDA  → https://fdc.nal.usda.gov/api-guide.html  (instant, no credit card)
  DeepL → https://www.deepl.com/pro-api            (free tier: 500k chars/month)
"""

import os
import sys
import time
import uuid
import requests
import deepl
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()

USDA_API_KEY  = os.environ.get("USDA_API_KEY", "")
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "")
DATABASE_URL  = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL", "")

if not USDA_API_KEY:
    sys.exit("❌  Falta USDA_API_KEY en .env")
if not DEEPL_API_KEY:
    sys.exit("❌  Falta DEEPL_API_KEY en .env")
if not DATABASE_URL:
    sys.exit("❌  Falta DATABASE_URL en .env")

if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

# How many foods to import (max 20,000 fits comfortably in DeepL free tier)
MAX_FOODS = 15_000

# USDA data types to fetch (Foundation + SR Legacy = raw, reliable ingredients)
DATA_TYPES = ["Foundation", "SR Legacy"]

# ── USDA category → Spanish group name ───────────────────────────────────────

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

# USDA nutrient IDs
NUT_PROTEIN = 1003
NUT_FAT     = 1004
NUT_CARBS   = 1005
NUT_KCAL    = 1008

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_nutrient(food: dict, nutrient_id: int) -> float | None:
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId") or n.get("nutrient", {}).get("id")
        if nid == nutrient_id:
            return round(n.get("value") or n.get("amount") or 0, 2)
    return None


def fetch_usda_page(page: int, page_size: int = 200) -> list[dict]:
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key":   USDA_API_KEY,
        "query":     "",
        "dataType":  DATA_TYPES,
        "pageSize":  page_size,
        "pageNumber": page,
    }
    r = requests.get(url, params=params, timeout=30)
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


def ensure_group(session, name: str, group_cache: dict) -> int | None:
    if not name:
        return None
    if name in group_cache:
        return group_cache[name]
    row = session.execute(
        text("SELECT id FROM group_foods WHERE name = :n"), {"n": name}
    ).fetchone()
    if row:
        gid = row[0]
    else:
        session.execute(
            text("INSERT INTO group_foods (name, status, created_at, updated_at) "
                 "VALUES (:n, 1, NOW(), NOW())"),
            {"n": name},
        )
        session.commit()
        gid = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
    group_cache[name] = gid
    return gid

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    engine  = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    translator = deepl.Translator(DEEPL_API_KEY)
    group_cache: dict[str, int] = {}

    print(f"🚀  Importando hasta {MAX_FOODS:,} alimentos de USDA FoodData Central...\n")

    page       = 1
    page_size  = 200
    total_done = 0
    skipped    = 0

    existing = set(
        row[0] for row in session.execute(
            text("SELECT comments FROM aliments WHERE comments LIKE 'usda:%'")
        ).fetchall()
    )
    print(f"   Ya existen {len(existing):,} alimentos USDA en la base de datos.\n")

    while total_done < MAX_FOODS:
        foods = fetch_usda_page(page, page_size)
        if not foods:
            print("✅  No hay más páginas en USDA.")
            break

        # Filter already imported
        new_foods = [f for f in foods if f"usda:{f['fdcId']}" not in existing]
        skipped  += len(foods) - len(new_foods)

        if not new_foods:
            page += 1
            continue

        # Translate names in batch
        en_names = [f.get("description", "Unknown") for f in new_foods]
        print(f"   Página {page}: {len(new_foods)} nuevos → traduciendo…")
        es_names = translate_batch(translator, en_names)

        # Insert
        batch = []
        for food, es_name in zip(new_foods, es_names):
            category_en = food.get("foodCategory") or food.get("foodCategoryLabel") or ""
            group_name  = CATEGORY_MAP.get(category_en, "Otros")
            group_id    = ensure_group(session, group_name, group_cache)

            proteins = get_nutrient(food, NUT_PROTEIN)
            fats     = get_nutrient(food, NUT_FAT)
            carbs    = get_nutrient(food, NUT_CARBS)
            kcal     = get_nutrient(food, NUT_KCAL)

            batch.append({
                "id":            str(uuid.uuid4()),
                "name":          es_name[:255],
                "group_food_id": group_id,
                "proteins":      proteins,
                "carbohydrates": carbs,
                "fats":          fats,
                "calories":      kcal,
                "quantity":      100.0,
                "comments":      f"usda:{food['fdcId']}",
            })

        session.execute(
            text("""
                INSERT INTO aliments
                    (id, name, group_food_id, proteins, carbohydrates, fats,
                     calories, quantity, comments, created_at, updated_at)
                VALUES
                    (:id, :name, :group_food_id, :proteins, :carbohydrates, :fats,
                     :calories, :quantity, :comments, NOW(), NOW())
                ON DUPLICATE KEY UPDATE name = name
            """),
            batch,
        )
        session.commit()

        total_done += len(new_foods)
        existing.update(f"usda:{f['fdcId']}" for f in new_foods)
        print(f"   ✔  {total_done:,} alimentos importados hasta ahora")

        if total_done >= MAX_FOODS:
            break

        page += 1
        time.sleep(0.3)  # be polite to USDA API

    session.close()
    print(f"\n🎉  Importación completa: {total_done:,} alimentos nuevos, {skipped:,} ya existían.")

    # Summary by group
    engine2 = create_engine(DATABASE_URL)
    with engine2.connect() as conn:
        rows = conn.execute(text(
            "SELECT g.name, COUNT(a.id) "
            "FROM aliments a LEFT JOIN group_foods g ON a.group_food_id = g.id "
            "GROUP BY g.name ORDER BY COUNT(a.id) DESC"
        )).fetchall()
    print("\n📊  Alimentos por grupo:")
    for name, count in rows:
        print(f"   {name or 'Sin grupo':<35} {count:>6,}")


if __name__ == "__main__":
    main()
