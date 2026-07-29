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
# Qué momento corresponde a cada comida.
MEAL_MOMENT_BY_NAME = {
    "Desayuno": "desayuno",
    "Media mañana": "snack",
    "Merienda": "snack",
    "Recena": "snack",
    "Comida": "principal",
    "Cena": "principal",
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

# Hacia dónde cargar las calorías. El coach lo elige al generar; "equilibrado"
# es el reparto de MEAL_SPLITS, y el resto lo desplaza sin cambiar el total.
DISTRIBUTIONS = {
    "balanced": None,
    "big_breakfast": {"desayuno": 1.55, "principal": 0.85},
    "big_lunch": {"desayuno": 0.75, "principal": 1.15},
    "light_dinner": {"cena": 0.6, "desayuno": 1.2},
}

# ── Momentos del día ─────────────────────────────────────────────────────────
# El reparto de macros por sí solo propone carne de vacuno para desayunar:
# cuadra las calorías pero no es un desayuno. Cada alimento encaja en unos
# momentos concretos, y el coach puede fijarlo por alimento (`meal_moments`);
# cuando no lo ha hecho, se deduce del nombre con estas listas.
MOMENTS = ("desayuno", "snack", "principal")

# Típicos de desayuno y de media mañana/merienda.
BREAKFAST_TERMS = [
    "avena", "cereal", "muesli", "granola", "pan", "tostada", "biscote", "galleta",
    "leche", "yogur", "kefir", "queso fresco", "requeson", "cuajada", "huevo",
    "tortilla", "clara", "fruta", "manzana", "platano", "banana", "naranja", "pera",
    "fresa", "arandano", "kiwi", "mandarina", "melocoton", "uva", "mango", "piña",
    "sandia", "melon", "zumo", "cafe", "te ", "cacao", "chocolate", "miel",
    "mermelada", "mantequilla", "aguacate", "almendra", "nuez", "avellana",
    "anacardo", "pistacho", "cacahuete", "crema de", "batido", "proteina",
    "tortita", "crepe", "pavo", "jamon", "salmon ahumado", "aceite de oliva",
    "semilla", "chia", "lino", "datil", "pasa", "higo", "arroz inflado", "espelta",
]

# Platos principales: comida y cena. Nadie desayuna lentejas.
MAIN_TERMS = [
    "arroz", "pasta", "espagueti", "macarron", "fideo", "quinoa", "cuscus", "bulgur",
    "patata", "boniato", "yuca", "platano macho", "lenteja", "garbanzo", "alubia",
    "judia", "frijol", "soja", "tofu", "seitan", "tempeh",
    "pollo", "pavo entero", "ternera", "vacuno", "res", "cerdo", "lomo", "solomillo",
    "chuleta", "costilla", "cordero", "conejo", "higado", "carne", "hamburguesa",
    "albondiga", "merluza", "bacalao", "atun", "salmon", "dorada", "lubina", "sardina",
    "caballa", "gamba", "langostino", "mejillon", "calamar", "pulpo", "marisco",
    "brocoli", "espinaca", "acelga", "judia verde", "coliflor", "calabacin",
    "berenjena", "pimiento", "tomate", "lechuga", "zanahoria", "cebolla", "champiñon",
    "esparrago", "alcachofa", "col ", "repollo", "guisante", "haba", "puerro",
    # También aparecen en desayunos: al estar en las dos listas valen para todo.
    "huevo", "tortilla", "clara", "aceite", "aguacate", "queso", "jamon", "pavo",
]

# Alimentos que excluye cada patología. Solo se listan las que se resuelven
# quitando alimentos; las que se manejan ajustando macros o sodio (diabetes,
# hipertensión, insuficiencia renal…) no entran aquí y las decide el coach.
# La coincidencia es por trozo de nombre, sin acentos ni mayúsculas.
PATHOLOGY_EXCLUSIONS = {
    "celiaca": ["trigo", "harina", "pan", "pasta", "cebada", "centeno", "espelta",
                "cuscus", "semola", "avena", "galleta", "cerveza", "bulgur", "seitan"],
    "gluten": ["trigo", "harina", "pan", "pasta", "cebada", "centeno", "espelta",
               "cuscus", "semola", "avena", "galleta", "cerveza", "bulgur", "seitan"],
    "lactosa": ["leche", "queso", "yogur", "nata", "mantequilla", "cuajada",
                "requeson", "helado", "bechamel"],
    "frutos secos": ["almendra", "nuez", "avellana", "anacardo", "pistacho",
                     "cacahuete", "mani", "pinon", "macadamia"],
    "gota": ["higado", "riñon", "molleja", "viscera", "marisco", "gamba", "langostino",
             "mejillon", "sardina", "anchoa", "boqueron", "caballa", "arenque"],
}

# Aviso para las patologías que NO se resuelven quitando alimentos: el plan
# cuadra los macros, pero el ajuste fino es criterio del coach.
PATHOLOGY_ADVICE = {
    "diabetes": "reparte los carbohidratos entre las comidas y prioriza los de bajo índice glucémico.",
    "insulina": "reparte los carbohidratos y evita concentrarlos en una sola comida.",
    "sop": "prioriza carbohidratos de bajo índice glucémico y suficiente proteína.",
    "hipertension": "vigila la sal y los alimentos procesados; el plan no controla el sodio.",
    "hipercolesterolemia": "limita las grasas saturadas y prioriza las insaturadas.",
    "renal": "revisa el objetivo de proteína: puede ser demasiado alto para su función renal.",
    "higado graso": "reduce azúcares simples y alcohol.",
    "hipotiroidismo": "vigila el yodo y el consumo de crucíferas crudas.",
    "anemia": "acompaña el hierro con vitamina C y sepáralo del café y los lácteos.",
    "osteoporosis": "asegura calcio y vitamina D suficientes.",
    "crohn": "ajusta la fibra a su tolerancia en cada fase.",
    "colitis": "ajusta la fibra a su tolerancia en cada fase.",
    "sibo": "revisa los fermentables (FODMAP) según su fase de tratamiento.",
    "reflujo": "evita comidas copiosas y muy grasas por la noche.",
    "gota": "mantén buena hidratación y limita el alcohol.",
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


def exclusions_for(pathologies) -> list:
    """Términos a excluir según las patologías del cliente.

    `pathologies` son los nombres del catálogo ("Enfermedad celíaca",
    "Intolerancia a la lactosa"…); se busca la clave dentro del nombre.
    """
    fuera = []
    for nombre in pathologies or []:
        n = _norm(str(nombre))
        for clave, alimentos in PATHOLOGY_EXCLUSIONS.items():
            if clave in n:
                fuera.extend(alimentos)
    return fuera


def warnings_for(pathologies) -> list:
    """Avisos a mostrar al principio de la dieta, uno por patología.

    `applied` distingue lo que el generador ya ha hecho (excluir alimentos) de
    lo que queda en manos del coach (ajustar macros, sodio, fibra…).
    """
    avisos = []
    for nombre in pathologies or []:
        n = _norm(str(nombre))
        excluidos = []
        for clave, alimentos in PATHOLOGY_EXCLUSIONS.items():
            if clave in n:
                excluidos.extend(alimentos)
        consejo = next((c for clave, c in PATHOLOGY_ADVICE.items() if clave in n), None)
        if excluidos:
            muestra = ", ".join(sorted(set(excluidos))[:6])
            texto = f"Se han excluido del plan alimentos con {muestra}…"
            if consejo:
                texto += f" Además, {consejo}"
            avisos.append({"pathology": str(nombre), "applied": True, "text": texto})
        elif consejo:
            avisos.append({"pathology": str(nombre), "applied": False,
                           "text": f"El plan no lo ajusta solo: {consejo}"})
        else:
            avisos.append({"pathology": str(nombre), "applied": False,
                           "text": "Revisa el plan teniendo en cuenta esta condición."})
    return avisos


def moments_for(aliment) -> list:
    """Momentos del día en los que encaja un alimento.

    Manda lo que haya fijado el coach en `meal_moments`; si está vacío se
    deduce del nombre. Un alimento que no encaje en ninguna lista vale para
    todo, que es la opción prudente: mejor proponerlo que descartarlo.
    """
    fijado = getattr(aliment, "meal_moments", None)
    if fijado:
        elegidos = [m.strip().lower() for m in str(fijado).split(",")]
        elegidos = [m for m in elegidos if m in MOMENTS]
        if elegidos:
            return elegidos

    nombre = _norm(f"{aliment.name} {getattr(aliment, 'brand', '') or ''}")
    desayuno = any(t in nombre for t in BREAKFAST_TERMS)
    principal = any(t in nombre for t in MAIN_TERMS)
    if desayuno and not principal:
        return ["desayuno", "snack"]
    if principal and not desayuno:
        return ["principal"]
    if desayuno and principal:
        # Ambiguo (huevo, jamón, aguacate, frutos secos): sirve para todo.
        return list(MOMENTS)
    return list(MOMENTS)


def is_allowed(aliment, restrictions: list) -> bool:
    nombre = _norm(f"{aliment.name} {getattr(aliment, 'brand', '') or ''}")
    # Un producto que se anuncia "sin gluten" o "sin lactosa" sigue valiendo.
    if "sin gluten" in nombre or "sin lactosa" in nombre:
        return True
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


def _splits_for(meal_count: int, distribution: Optional[str]) -> list:
    """Reparto de calorías, desplazado según la directriz del coach."""
    base = list(MEAL_SPLITS[meal_count])
    factores = DISTRIBUTIONS.get(distribution or "balanced")
    if not factores:
        return base
    nombres = MEAL_NAMES[meal_count]
    ajustado = []
    for (nombre, _), peso in zip(nombres, base):
        momento = MEAL_MOMENT_BY_NAME.get(nombre, "principal")
        factor = factores.get(nombre.lower(), factores.get(momento, 1.0))
        ajustado.append(peso * factor)
    total = sum(ajustado) or 1
    return [p / total for p in ajustado]   # se renormaliza: el total no cambia


def build_diet(*, aliments: list, kcal: float, proteins: float, carbs: float,
               fats: float, meal_count: int = 4, restrictions: Optional[list] = None,
               seed: Optional[int] = None, distribution: Optional[str] = None) -> dict:
    """Devuelve {meals:[...], totals:{...}} o lanza ValueError si falta catálogo."""
    restrictions = restrictions or []
    meal_count = max(2, min(int(meal_count or 4), 6))
    rnd = random.Random(seed if seed is not None else 0)

    # Cada alimento se guarda con los momentos del día en los que encaja, para
    # no proponer ternera en el desayuno ni cereales de desayuno en la cena.
    pools = {"protein": [], "carb": [], "fat": [], "veg": []}
    for a in aliments:
        if not is_allowed(a, restrictions):
            continue
        rol = classify(a)
        if rol:
            pools[rol].append((a, moments_for(a)))
    if not pools["protein"] or not pools["carb"]:
        raise ValueError(
            "El catálogo no tiene suficientes alimentos con macros para construir la dieta "
            "(hacen falta fuentes de proteína y de carbohidrato)."
        )
    for v in pools.values():
        rnd.shuffle(v)

    splits = _splits_for(meal_count, distribution)
    nombres = MEAL_NAMES[meal_count]
    # Se reparten los macros con el mismo peso que las calorías.
    usados = {"protein": 0, "carb": 0, "fat": 0, "veg": 0}

    def take(rol, momento, obligatorio=True):
        """Siguiente alimento del rol que encaje en ese momento del día.

        Rota el catálogo para no repetir. Si ninguno encaja: en los alimentos
        obligatorios (los que aportan los macros) se acepta cualquiera antes que
        dejar la comida coja; en los opcionales, como la guarnición, se prefiere
        omitirla a colar espinacas en el desayuno.
        """
        pool = pools[rol]
        if not pool:
            return None
        aptos = [a for a, momentos in pool if momento in momentos]
        if not aptos:
            if not obligatorio:
                return None
            aptos = [a for a, _ in pool]
        a = aptos[usados[rol] % len(aptos)]
        usados[rol] += 1
        return a

    meals = []
    for i, share in enumerate(splits):
        obj_p, obj_c, obj_f = proteins * share, carbs * share, fats * share
        nombre, hora = nombres[i]
        momento = MEAL_MOMENT_BY_NAME.get(nombre, "principal")
        pequena = share < 0.2  # snacks: dos alimentos bastan
        detail = []
        rest_p, rest_c, rest_f = obj_p, obj_c, obj_f

        # 1) Proteína: fija los gramos para cubrir la proteína de la comida.
        pa = take("protein", momento)
        if pa and (pa.proteins or 0) > 0:
            g = _round_step(rest_p / (pa.proteins / 100.0))
            if g:
                detail.append((pa, g))
                _, p, c, f = _macros(pa, g)
                rest_p -= p
                rest_c -= c
                rest_f -= f

        # 2) Carbohidrato: cubre lo que queda de carbos.
        ca = take("carb", momento)
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
            fa = take("fat", momento, obligatorio=False)
            if fa and (fa.fats or 0) > 0:
                g = _round_step(rest_f / (fa.fats / 100.0))
                if g:
                    detail.append((fa, g))

        # 4) Verdura de acompañamiento en las comidas principales.
        if not pequena and pools["veg"]:
            va = take("veg", momento, obligatorio=False)
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
