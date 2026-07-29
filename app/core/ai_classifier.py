"""Clasificación de alimentos por momento del día con IA.

El generador de dietas ya sabe respetar el campo `meal_moments` de cada
alimento; el problema era rellenarlo. La heurística por nombre no da abasto con
un catálogo real: "Gazpacho" no casa con ningún término y acaba valiendo para
todo, y "Crema de calabaza" casa con "crema de" (que estaba pensado para la de
cacahuete) y acaba siendo un desayuno.

Esto lo resuelve pidiéndole la clasificación a un modelo UNA VEZ por alimento,
no una vez por dieta. Las dietas se siguen construyendo con el algoritmo: gratis,
instantáneas y explicables. Y en el prompt solo viajan nombres de alimentos y
macros — ningún dato del cliente sale de aquí.
"""
from typing import Optional

from app.config import settings

MOMENTOS = ("desayuno", "snack", "principal")

# Se responde por índice dentro del lote, no por id: los ids son UUID de 36
# caracteres que multiplicarían el coste y que el modelo puede transcribir mal.
MOMENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "alimentos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "description": "Número del alimento en la lista"},
                    "momentos": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(MOMENTOS)},
                        "description": "Momentos del día en los que encaja",
                    },
                },
                "required": ["n", "momentos"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["alimentos"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """Clasificas alimentos según en qué momento del día encajan en una dieta española.

Los tres momentos:
- desayuno: lo que se desayuna de verdad — cereales, avena, pan y tostadas, lácteos, fruta, huevos, café, cacao, frutos secos, mermelada, miel.
- snack: media mañana y merienda — picoteo ligero, fruta, yogures, barritas, frutos secos, batidos.
- principal: comida y cena — legumbres, arroz, pasta, patata, carnes, pescados, verduras, y sopas y cremas saladas.

Reglas:
- Un alimento puede encajar en varios momentos. El huevo, el aguacate, el aceite de oliva o el queso valen para casi todo; las lentejas solo en principal; los cereales de desayuno solo en desayuno.
- Piensa en cómo se come realmente, no en si los macros cuadran. La ternera cuadra de macros en un desayuno, pero nadie desayuna ternera: eso es exactamente el error que hay que evitar.
- Las cremas y sopas saladas (de calabaza, de calabacín, gazpacho, salmorejo) son `principal` aunque lleven "crema" en el nombre.
- Los platos preparados y bocadillos van al momento en que se comerían, normalmente `principal`.
- Si no reconoces el alimento, deduce por el tipo de comida que parece por el nombre y los macros. Nunca devuelvas una lista de momentos vacía.

Devuelve una entrada por cada alimento de la lista, con su mismo número."""


def classify_enabled() -> bool:
    """Requiere clave Y su propio interruptor.

    Es un interruptor distinto al de generar dietas con IA a propósito: esto se
    paga una vez por alimento y no manda datos de ningún cliente, así que puede
    estar encendido sin que lo esté el generador completo.
    """
    return bool(settings.ANTHROPIC_API_KEY) and bool(settings.AI_CLASSIFY_ENABLED)


def _fmt(n: int, a) -> str:
    marca = f" ({a.brand})" if getattr(a, "brand", None) else ""
    return (
        f"{n}. {a.name}{marca}"
        f" — {round(a.calories or 0)} kcal,"
        f" P {round(a.proteins or 0, 1)},"
        f" C {round(a.carbohydrates or 0, 1)},"
        f" G {round(a.fats or 0, 1)} por 100 g"
    )


def build_prompt(aliments: list) -> str:
    lineas = "\n".join(_fmt(i, a) for i, a in enumerate(aliments))
    return f"Clasifica estos {len(aliments)} alimentos:\n\n{lineas}"


def classify(aliments: list) -> dict:
    """Devuelve {id_alimento: "desayuno,snack"} para el lote recibido.

    Los alimentos que el modelo no devuelva, o devuelva sin momentos válidos,
    quedan fuera del diccionario: el que llama los deja como estaban en vez de
    escribirles un valor inventado.
    """
    if not aliments:
        return {}

    import json

    import anthropic

    api = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = api.messages.create(
        model=settings.ANTHROPIC_CLASSIFY_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": MOMENTS_SCHEMA}},
        messages=[{"role": "user", "content": build_prompt(aliments)}],
    )

    if message.stop_reason == "refusal":
        raise RuntimeError("La IA no pudo clasificar este lote de alimentos.")

    texto = next((b.text for b in message.content if b.type == "text"), "")
    if not texto:
        raise RuntimeError("La IA no devolvió ninguna clasificación.")

    datos = json.loads(texto)
    salida: dict = {}
    for fila in datos.get("alimentos", []):
        n = fila.get("n")
        if not isinstance(n, int) or not (0 <= n < len(aliments)):
            continue
        momentos = [m for m in fila.get("momentos", []) if m in MOMENTOS]
        if not momentos:
            continue
        # Orden fijo para que el valor guardado no dependa del orden que
        # devuelva el modelo y los tests sean reproducibles.
        ordenados = [m for m in MOMENTOS if m in momentos]
        salida[aliments[n].id] = ",".join(ordenados)
    return salida


def classify_one(aliment) -> Optional[str]:
    """Clasifica un solo alimento. Devuelve None si no se pudo."""
    return classify([aliment]).get(aliment.id)
