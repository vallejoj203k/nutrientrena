"""Generador de dietas por algoritmo, sin IA ni servicios externos.

Construir un plan que cuadre con unas calorías y unos macros es un problema de
reparto con restricciones, no de lenguaje: se eligen alimentos del catálogo por
su papel (proteína, carbohidrato, grasa, verdura), se reparten entre las comidas
según el peso de cada una y se resuelven los gramos para llegar al objetivo.

Coste cero, respuesta inmediata y resultado reproducible: con los mismos datos
sale el mismo plan, salvo que se pida otra variante con `seed`.
"""
import random
import unicodedata
from typing import Optional

# Reparto de calorías por comida según cuántas haya. El desayuno y la comida
# cargan más que un snack, que es como se planifica en la práctica.
MEAL_SPLITS = {
    2: [0.45, 0.55],
    3: [0.30, 0.40, 0.30],
    4: [0.25, 0.15, 0.35, 0.25],
    5: [0.22, 0.12, 0.33, 0.11, 0.22],
    6: [0.20, 0.10, 0.30, 0.10, 0.20, 0.10],
}
MEAL_NAMES = {
    2: [("Comida", "14:00"), ("Cena", "21:00")],
    3: [("Desayuno", "08:00"), ("Comida", "14:00"), ("Cena", "21:00")],
    4: [("Desayuno", "08:00"), ("Media mañana", "11:00"), ("Comida", "14:00"), ("Cena", "21:00")],
    5: [("Desayuno", "08:00"), ("Media mañana", "11:00"), ("Comida", "14:00"),
        ("Merienda", "17:30"), ("Cena", "21:00")],
    6: [("Desayuno", "08:00"), ("Media mañana", "11:00"), ("Comida", "14:00"),
        ("Merienda", "17:30"), ("Cena", "21:00"), ("Recena", "23:00")],
}

# Cantidades a las que se redondea: las que un cliente puede pesar sin volverse loco.
STEPS = [10, 15, 20, 25, 30, 40, 50, 60, 70, 75, 80, 100, 125, 150, 175, 200, 225, 250, 300]


def _norm(t: str) -> str:
    """Minúsculas y sin acentos, para comparar nombres con las restricciones."""
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def parse_restrictions(*fields) -> list:
    """Convierte los campos de alergias/intolerancias/disgustos en términos."""
    out = []
    for f in fields:
        for token in str(f or "").replace(";", ",").split(","):
            token = _norm(token).strip()
            if len(token) >= 3:
                out.append(token)
    return out


def is_allowed(aliment, restrictions: list) -> bool:
    nombre = _norm(f"{aliment.name} {getattr(aliment, 'brand', '') or ''}")
    return not any(r in nombre for r in restrictions)


def classify(a) -> Optional[str]:
    """Papel del alimento según de dónde vengan sus calorías."""
    k = a.calories or 0
    p, c, f = a.proteins or 0, a.carbohydrates or 0, a.fats or 0
    if k <= 0 or (p + c + f) <= 0:
        return None
    kp, kc, kf = p * 4, c * 4, f * 9
    total = kp + kc + kf
    if total <= 0:
        return None
    # Muy pocas calorías por 100 g: es guarnición/verdura, aporta volumen y fibra.
    if k < 60 and c * 4 / total > 0.4:
        return "veg"
    if kp / total >= 0.40:
        return "protein"
    if kf / total >= 0.50:
        return "fat"
    if kc / total >= 0.50:
        return "carb"
    return "protein" if kp >= kf else "fat"


def _round_step(g: float) -> int:
    if g <= 0:
        return 0
    return min(STEPS, key=lambda s: abs(s - g))


def _macros(a, grams: float) -> tuple:
    f = grams / 100.0
    return ((a.calories or 0) * f, (a.proteins or 0) * f,
            (a.carbohydrates or 0) * f, (a.fats or 0) * f)


def build_diet(*, aliments: list, kcal: float, proteins: float, carbs: float,
               fats: float, meal_count: int = 4, restrictions: Optional[list] = None,
               seed: Optional[int] = None) -> dict:
    """Devuelve {meals:[...], totals:{...}} o lanza ValueError si falta catálogo."""
    restrictions = restrictions or []
    meal_count = max(2, min(int(meal_count or 4), 6))
    rnd = random.Random(seed if seed is not None else 0)

    pools = {"protein": [], "carb": [], "fat": [], "veg": []}
    for a in aliments:
        if not is_allowed(a, restrictions):
            continue
        rol = classify(a)
        if rol:
            pools[rol].append(a)
    if not pools["protein"] or not pools["carb"]:
        raise ValueError(
            "El catálogo no tiene suficientes alimentos con macros para construir la dieta "
            "(hacen falta fuentes de proteína y de carbohidrato)."
        )
    for v in pools.values():
        rnd.shuffle(v)

    splits = MEAL_SPLITS[meal_count]
    nombres = MEAL_NAMES[meal_count]
    # Se reparten los macros con el mismo peso que las calorías.
    usados = {"protein": 0, "carb": 0, "fat": 0, "veg": 0}

    def take(rol):
        """Va rotando el catálogo para no repetir el mismo alimento cada comida."""
        pool = pools[rol]
        if not pool:
            return None
        a = pool[usados[rol] % len(pool)]
        usados[rol] += 1
        return a

    meals = []
    for i, share in enumerate(splits):
        obj_p, obj_c, obj_f = proteins * share, carbs * share, fats * share
        nombre, hora = nombres[i]
        pequena = share < 0.2  # snacks: dos alimentos bastan
        detail = []
        rest_p, rest_c, rest_f = obj_p, obj_c, obj_f

        # 1) Proteína: fija los gramos para cubrir la proteína de la comida.
        pa = take("protein")
        if pa and (pa.proteins or 0) > 0:
            g = _round_step(rest_p / (pa.proteins / 100.0))
            if g:
                detail.append((pa, g))
                _, p, c, f = _macros(pa, g)
                rest_p -= p
                rest_c -= c
                rest_f -= f

        # 2) Carbohidrato: cubre lo que queda de carbos.
        ca = take("carb")
        if ca and (ca.carbohydrates or 0) > 0 and rest_c > 3:
            g = _round_step(rest_c / (ca.carbohydrates / 100.0))
            if g:
                detail.append((ca, g))
                _, p, c, f = _macros(ca, g)
                rest_p -= p
                rest_c -= c
                rest_f -= f

        # 3) Grasa: solo si falta bastante y no es un snack.
        if rest_f > 4 and not pequena:
            fa = take("fat")
            if fa and (fa.fats or 0) > 0:
                g = _round_step(rest_f / (fa.fats / 100.0))
                if g:
                    detail.append((fa, g))

        # 4) Verdura de acompañamiento en las comidas principales.
        if not pequena and pools["veg"]:
            va = take("veg")
            if va:
                detail.append((va, 150))

        meals.append({"name": nombre, "time": hora, "items": detail})

    # Ajuste final: se escalan los gramos para clavar las calorías objetivo.
    def total_kcal():
        return sum(_macros(a, g)[0] for m in meals for a, g in m["items"])

    actual = total_kcal()
    if actual > 0 and kcal > 0:
        factor = kcal / actual
        if 0.5 <= factor <= 2.0 and abs(factor - 1) > 0.03:
            for m in meals:
                m["items"] = [(a, _round_step(g * factor)) for a, g in m["items"]]

    out_meals, tot = [], [0.0, 0.0, 0.0, 0.0]
    for m in meals:
        detail = []
        for a, g in m["items"]:
            if g <= 0:
                continue
            k, p, c, f = _macros(a, g)
            tot = [tot[0] + k, tot[1] + p, tot[2] + c, tot[3] + f]
            detail.append({
                "aliment_id": str(a.id), "name": a.name, "quantity_calc": int(g),
                "calories": round(k), "proteins": round(p, 1),
                "carbohydrates": round(c, 1), "fats": round(f, 1),
            })
        if detail:
            out_meals.append({"name": m["name"], "time": m["time"], "detail": detail})

    return {
        "meals": out_meals,
        "totals": {"calories": round(tot[0]), "proteins": round(tot[1], 1),
                   "carbs": round(tot[2], 1), "fats": round(tot[3], 1)},
    }
