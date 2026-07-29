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

Por eso mismo admite dos proveedores: como no se manda nada personal, vale un
servicio gratuito para probar que la idea funciona antes de pagar nada. El
prompt, el esquema y el parseo son los mismos en ambos; solo cambia la llamada.
"""
from typing import Optional

import httpx

from app.config import settings

MOMENTOS = ("desayuno", "snack", "principal")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

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

# Anthropic acepta el esquema como parámetro; en la API de Groq (compatible con
# OpenAI) se pide JSON y la forma se describe en el propio prompt.
FORMATO_JSON = """
Responde ÚNICAMENTE con un objeto JSON con esta forma exacta, sin texto alrededor:
{"alimentos": [{"n": 0, "momentos": ["desayuno", "snack"]}, {"n": 1, "momentos": ["principal"]}]}"""


def _proveedor() -> str:
    return (settings.AI_CLASSIFY_PROVIDER or "anthropic").strip().lower()


def _api_key() -> Optional[str]:
    return settings.GROQ_API_KEY if _proveedor() == "groq" else settings.ANTHROPIC_API_KEY


def key_var_name() -> str:
    """Nombre de la variable que falta, para poder decírselo a quien configura."""
    return "GROQ_API_KEY" if _proveedor() == "groq" else "ANTHROPIC_API_KEY"


def classify_enabled() -> bool:
    """Requiere la clave del proveedor elegido Y su propio interruptor.

    Es un interruptor distinto al de generar dietas con IA a propósito: esto se
    paga una vez por alimento y no manda datos de ningún cliente, así que puede
    estar encendido sin que lo esté el generador completo.
    """
    return bool(_api_key()) and bool(settings.AI_CLASSIFY_ENABLED)


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


def _preguntar_anthropic(prompt: str) -> str:
    import anthropic

    api = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = api.messages.create(
        model=settings.ANTHROPIC_CLASSIFY_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": MOMENTS_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if message.stop_reason == "refusal":
        raise RuntimeError("La IA no pudo clasificar este lote de alimentos.")
    return next((b.text for b in message.content if b.type == "text"), "")


class RateLimited(RuntimeError):
    """El proveedor pide esperar. `seconds` es cuánto, para poder reanudar."""

    def __init__(self, seconds: int):
        self.seconds = seconds
        super().__init__(
            f"Se ha alcanzado el límite por minuto del plan gratuito. "
            f"Reanudando en {seconds} s."
        )


def _segundos_de_espera(r) -> int:
    """Lee retry-after; si no viene o es raro, un minuto, que es la ventana."""
    try:
        return max(1, min(int(float(r.headers.get("retry-after", 60))), 300))
    except (TypeError, ValueError):
        return 60


def _preguntar_groq(prompt: str) -> str:
    """API de Groq, compatible con OpenAI. Sin SDK: es una única petición."""
    r = httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json={
            "model": settings.GROQ_CLASSIFY_MODEL,
            # Clasificar no es creativo: se quiere el mismo resultado siempre.
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + "\n" + FORMATO_JSON},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120,
    )
    if r.status_code == 429:
        # El límite del plan gratuito es por minuto. Se levanta un error que
        # lleva la espera dentro, para que quien llama pueda reanudar solo en
        # vez de dejar el catálogo a medias.
        raise RateLimited(_segundos_de_espera(r))
    if r.status_code != 200:
        raise RuntimeError(f"Groq respondió {r.status_code}: {r.text[:200]}")
    try:
        return r.json()["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, ValueError) as e:
        raise RuntimeError(f"Respuesta inesperada de Groq: {e}")


def classify(aliments: list) -> dict:
    """Devuelve {id_alimento: "desayuno,snack"} para el lote recibido.

    Los alimentos que el modelo no devuelva, o devuelva sin momentos válidos,
    quedan fuera del diccionario: el que llama los deja como estaban en vez de
    escribirles un valor inventado. Vale igual para los dos proveedores, porque
    de ninguno de los dos hay que fiarse más que del otro.
    """
    if not aliments:
        return {}

    import json

    prompt = build_prompt(aliments)
    texto = _preguntar_groq(prompt) if _proveedor() == "groq" else _preguntar_anthropic(prompt)
    if not texto:
        raise RuntimeError("La IA no devolvió ninguna clasificación.")

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"La IA no devolvió JSON válido: {e}")
    if not isinstance(datos, dict):
        raise RuntimeError("La IA no devolvió un objeto JSON.")
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
