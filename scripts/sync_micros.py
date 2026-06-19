"""
Sync micronutrients from USDA FoodData Central directly into Railway DB.

Setup:
  pip install sqlalchemy pymysql httpx python-dotenv

.env:
  MYSQL_URL=mysql+pymysql://user:pass@host:port/db
  USDA_API_KEY=your_key

Usage:
  python scripts/sync_micros.py
  python scripts/sync_micros.py --batch 50   # aliments per run (default: all)
  python scripts/sync_micros.py --dry-run    # show what would sync, no writes
"""

import argparse
import asyncio
import os
import sys
import time

import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

RAW_URL = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL") or ""
if not RAW_URL:
    sys.exit("❌  Falta DATABASE_URL o MYSQL_URL en .env")
if RAW_URL.startswith("mysql://"):
    RAW_URL = RAW_URL.replace("mysql://", "mysql+pymysql://", 1)
if RAW_URL.startswith("postgres://"):
    sys.exit("❌  Este script es solo para MySQL")

USDA_API_KEY = os.environ.get("USDA_API_KEY", "")
if not USDA_API_KEY:
    sys.exit("❌  Falta USDA_API_KEY en .env")

USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

NUTRIENT_MAP = {
    "vita": 1106, "vitb1": 1165, "vitb2": 1166, "vitb3": 1167,
    "vitb5": 1170, "vitb6": 1175, "vitb9": 1177, "vitb12": 1178,
    "vitc": 1162, "vitd": 1114, "vite": 1109, "vitk": 1185,
    "calcium": 1087, "copper": 1098, "iron": 1089, "magnesium": 1090,
    "manganese": 1101, "phosphorus": 1091, "potassium": 1092,
    "selenium": 1103, "sodium": 1093, "zinc": 1095,
    "water": 1051, "fiber": 1079, "cholesterol": 1253,
    "saturated_fats": 1258, "mono_saturated_fats": 1292, "poli_saturated_fats": 1293,
}

MACRO_MAP = {
    "proteins": 1003, "carbohydrates": 1005, "fats": 1004, "calories": 1008,
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def usda_query(name: str) -> str:
    """Shorten a long translated name to a safe USDA search term."""
    short = name.split(",")[0].strip()
    for ch in ["«", "»", '"', "'", "/", "\\", "(", ")", "%"]:
        short = short.replace(ch, " ")
    short = " ".join(short.split())[:80]
    return short or name[:80]


def get_nutrient(food: dict, nutrient_id: int):
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId") or n.get("nutrient", {}).get("id")
        if nid == nutrient_id:
            val = n.get("value") or n.get("amount") or 0
            try:
                return round(float(val), 4)
            except (TypeError, ValueError):
                return None
    return None


async def search_food(client: httpx.AsyncClient, query: str):
    resp = await client.get(
        USDA_URL,
        params={
            "api_key": USDA_API_KEY,
            "query": query,
            "dataType": "Foundation,SR Legacy",
            "pageSize": 1,
            "pageNumber": 1,
        },
    )
    resp.raise_for_status()
    foods = resp.json().get("foods", [])
    return foods[0] if foods else None


# ── Main ───────────────────────────────────────────────────────────────────────

async def run(batch: int, dry_run: bool):
    engine = create_engine(RAW_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, name, proteins, carbohydrates, fats, calories "
            "FROM aliments "
            "WHERE parent_id IS NULL "
            "AND id NOT IN (SELECT aliment_id FROM aliment_descriptions)"
            + (f" LIMIT {batch}" if batch else "")
        )).fetchall()

    total = len(rows)
    if total == 0:
        print("✅  No hay alimentos pendientes de sincronizar.")
        return

    print(f"🔍  {total} alimentos pendientes{' (modo dry-run)' if dry_run else ''}\n")

    synced = 0
    not_found = []
    errors = []
    start = time.time()

    async with httpx.AsyncClient(timeout=15) as client:
        for i, row in enumerate(rows, 1):
            aliment_id, name, proteins, carbs, fats, calories = row
            query = usda_query(name)

            try:
                food = await search_food(client, query)
                if not food:
                    not_found.append(name)
                    print(f"  [{i}/{total}] ⚠  No encontrado: {name[:60]}")
                    await asyncio.sleep(0.25)
                    continue

                micros = {col: get_nutrient(food, nid) for col, nid in NUTRIENT_MAP.items()}
                macros = {col: get_nutrient(food, nid) for col, nid in MACRO_MAP.items()}

                non_null = {k: v for k, v in micros.items() if v is not None}
                if not non_null:
                    not_found.append(name)
                    print(f"  [{i}/{total}] ⚠  Sin micros: {name[:60]}")
                    await asyncio.sleep(0.25)
                    continue

                if not dry_run:
                    cols = ", ".join(non_null.keys())
                    placeholders = ", ".join(f":{k}" for k in non_null.keys())
                    updates = ", ".join(f"{k}=VALUES({k})" for k in non_null.keys())

                    with engine.begin() as conn:
                        # Update macros if missing
                        macro_updates = {}
                        if proteins is None and macros.get("proteins") is not None:
                            macro_updates["proteins"] = macros["proteins"]
                        if carbs is None and macros.get("carbohydrates") is not None:
                            macro_updates["carbohydrates"] = macros["carbohydrates"]
                        if fats is None and macros.get("fats") is not None:
                            macro_updates["fats"] = macros["fats"]
                        if calories is None and macros.get("calories") is not None:
                            macro_updates["calories"] = macros["calories"]
                        if macro_updates:
                            set_clause = ", ".join(f"{k}=:{k}" for k in macro_updates.keys())
                            conn.execute(
                                text(f"UPDATE aliments SET {set_clause} WHERE id=:id"),
                                {**macro_updates, "id": aliment_id},
                            )

                        conn.execute(
                            text(
                                f"INSERT INTO aliment_descriptions (aliment_id, {cols}) "
                                f"VALUES (:aliment_id, {placeholders}) "
                                f"ON DUPLICATE KEY UPDATE {updates}"
                            ),
                            {"aliment_id": aliment_id, **non_null},
                        )

                synced += 1
                print(f"  [{i}/{total}] ✅  {name[:60]}")
                await asyncio.sleep(0.25)

            except Exception as e:
                errors.append(f"{name[:60]}: {e}")
                print(f"  [{i}/{total}] ❌  {name[:60]}: {str(e)[:80]}")
                await asyncio.sleep(0.5)

    elapsed = time.time() - start
    print(f"\n{'─'*60}")
    print(f"✅  Sincronizados : {synced}")
    print(f"⚠   No encontrados: {len(not_found)}")
    print(f"❌  Con error     : {len(errors)}")
    print(f"⏱   Tiempo        : {elapsed:.0f}s")
    if errors:
        print("\nErrores detallados:")
        for e in errors:
            print(f"  • {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=0, help="Máximo de alimentos a procesar (0 = todos)")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué sincronizaría, sin escribir")
    args = parser.parse_args()
    asyncio.run(run(args.batch, args.dry_run))


if __name__ == "__main__":
    main()
