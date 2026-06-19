"""
USDA FoodData Central client.
Searches foods by name and maps nutrient IDs to AlimentDescription columns.
"""
import httpx
from typing import Optional

USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DATA_TYPES = ["Foundation", "SR Legacy"]

# USDA nutrient ID → AlimentDescription column
NUTRIENT_MAP: dict[str, int] = {
    "vita":                1106,
    "vitb1":               1165,
    "vitb2":               1166,
    "vitb3":               1167,
    "vitb5":               1170,
    "vitb6":               1175,
    "vitb9":               1177,
    "vitb12":              1178,
    "vitc":                1162,
    "vitd":                1114,
    "vite":                1109,
    "vitk":                1185,
    "calcium":             1087,
    "copper":              1098,
    "iron":                1089,
    "magnesium":           1090,
    "manganese":           1101,
    "phosphorus":          1091,
    "potassium":           1092,
    "selenium":            1103,
    "sodium":              1093,
    "zinc":                1095,
    "water":               1051,
    "fiber":               1079,
    "cholesterol":         1253,
    "saturated_fats":      1258,
    "mono_saturated_fats": 1292,
    "poli_saturated_fats": 1293,
}

MACRO_MAP: dict[str, int] = {
    "proteins":      1003,
    "carbohydrates": 1005,
    "fats":          1004,
    "calories":      1008,
}


def _extract_nutrient(food: dict, nutrient_id: int) -> Optional[float]:
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId") or n.get("nutrient", {}).get("id")
        if nid == nutrient_id:
            val = n.get("value") or n.get("amount") or 0
            try:
                return round(float(val), 4)
            except (TypeError, ValueError):
                return None
    return None


async def search_food(api_key: str, query: str) -> Optional[dict]:
    """Return the best USDA match for the given food name, or None."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            USDA_SEARCH_URL,
            params={
                "api_key":    api_key,
                "query":      query,
                "dataType":   ",".join(DATA_TYPES),
                "pageSize":   1,
                "pageNumber": 1,
            },
        )
        resp.raise_for_status()
        foods = resp.json().get("foods", [])
        return foods[0] if foods else None


def extract_micros(food: dict) -> dict:
    """Extract all micronutrient values from a USDA food dict."""
    return {col: _extract_nutrient(food, nid) for col, nid in NUTRIENT_MAP.items()}


def extract_macros(food: dict) -> dict:
    """Extract macronutrient values from a USDA food dict."""
    return {col: _extract_nutrient(food, nid) for col, nid in MACRO_MAP.items()}
