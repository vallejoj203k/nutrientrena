"""Generación de dietas con IA (Claude).

El modelo NO inventa alimentos ni hace las cuentas: se le entrega el catálogo
real de alimentos del coach y los objetivos ya calculados en la sección de
Nutrición, y solo decide qué alimentos usar y en qué cantidad. Los totales se
recalculan después con los valores de la base de datos, de modo que lo que ve
el coach siempre cuadra con los cálculos de la aplicación.
"""
from typing import Optional

import httpx

from app.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Esquema de la respuesta: se fuerza con structured outputs para que siempre
# llegue en esta forma y no haya que interpretar texto libre.
DIET_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Nombre corto y descriptivo de la dieta"},
        "notes": {"type": "string", "description": "Indicaciones del nutricionista, 2-3 frases"},
        "meals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Desayuno, Media mañana, Comida, Merienda, Cena…"},
                    "time": {"type": "string", "description": "Hora en formato HH:MM"},
                    "foods": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "aliment_id": {"type": "string", "description": "id exacto del catálogo"},
                                "grams": {"type": "number", "description": "Cantidad en gramos"},
                            },
                            "required": ["aliment_id", "grams"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name", "time", "foods"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "notes", "meals"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """Eres un nutricionista que prepara planes de alimentación diarios para los clientes de un coach.

Reglas que no puedes saltarte:
- Usa únicamente alimentos del catálogo que se te entrega, referenciados por su `id` exacto. No inventes alimentos ni ids.
- Respeta el objetivo de calorías y macros indicado. Un margen del 5 % es aceptable; por encima de eso el plan no sirve.
- Respeta el número de comidas pedido y reparte las calorías de forma razonable entre ellas (el desayuno y la comida suelen llevar más carga que un snack).
- No incluyas ningún alimento que choque con las alergias, intolerancias, patologías o preferencias del cliente.
- Usa cantidades realistas y redondeadas (30, 50, 75, 100, 125, 150, 200 g), no cifras como 87,3 g.
- Varía los alimentos entre comidas: no repitas el mismo en todas.

Las notas van dirigidas al cliente, en español, en un tono claro y cercano. No expliques tus cálculos: el sistema recalcula los totales por su cuenta."""


def _proveedor() -> str:
    return (settings.AI_DIET_PROVIDER or "anthropic").strip().lower()


def _api_key() -> Optional[str]:
    return settings.GROQ_API_KEY if _proveedor() == "groq" else settings.ANTHROPIC_API_KEY


def key_var_name() -> str:
    return "GROQ_API_KEY" if _proveedor() == "groq" else "ANTHROPIC_API_KEY"


def ai_enabled() -> bool:
    """Requiere clave Y el interruptor: la clave sola no basta para gastar."""
    return bool(_api_key()) and bool(settings.AI_DIET_ENABLED)


def _fmt_aliment(a) -> str:
    """Una línea por alimento, con sus macros por 100 g."""
    return (
        f"- id={a.id} | {a.name}"
        + (f" ({a.brand})" if getattr(a, "brand", None) else "")
        + f" | {round(a.calories or 0)} kcal"
        f" | P {round(a.proteins or 0, 1)}"
        f" | C {round(a.carbohydrates or 0, 1)}"
        f" | G {round(a.fats or 0, 1)}"
    )


def build_prompt(*, client: dict, target: dict, aliments: list) -> str:
    """Arma el mensaje con los datos del cliente, sus metas y el catálogo."""
    partes = []

    perfil = [f"- {k}: {v}" for k, v in client.items() if v not in (None, "", [])]
    partes.append("## Cliente\n" + ("\n".join(perfil) if perfil else "- Sin datos adicionales"))

    metas = [f"- Calorías: {round(target['kcal'])} kcal/día"]
    for clave, etiqueta in (("proteins", "Proteínas"), ("carbs", "Carbohidratos"), ("fats", "Grasas"), ("fiber", "Fibra")):
        if target.get(clave):
            metas.append(f"- {etiqueta}: {round(target[clave])} g")
    metas.append(f"- Número de comidas: {target.get('meal_count', 4)}")
    partes.append("## Objetivo diario (calculado por la aplicación)\n" + "\n".join(metas))

    partes.append(
        "## Catálogo de alimentos disponibles (valores por 100 g)\n"
        + "\n".join(_fmt_aliment(a) for a in aliments)
    )
    partes.append(
        "Construye el plan del día usando solo estos alimentos. Devuelve el resultado en el formato indicado."
    )
    return "\n\n".join(partes)


# En la API de Groq (compatible con OpenAI) el esquema no es un parámetro:
# se pide JSON y la forma se describe en el propio prompt.
FORMATO_JSON = """
Responde ÚNICAMENTE con un objeto JSON con esta forma, sin texto alrededor:
{"title": "...", "notes": "...", "meals": [{"name": "Desayuno", "time": "08:00",
 "foods": [{"aliment_id": "<id exacto del catálogo>", "grams": 60}]}]}"""


def _preguntar_anthropic(prompt: str) -> str:
    import anthropic

    api = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    # Streaming: el plan puede tardar y una petición normal se arriesga a que
    # expire la conexión.
    with api.messages.stream(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": DIET_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise RuntimeError("La IA no pudo generar este plan. Revisa los datos del cliente e inténtalo de nuevo.")
    return next((b.text for b in message.content if b.type == "text"), "")


def _preguntar_groq(prompt: str) -> str:
    r = httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json={
            "model": settings.GROQ_DIET_MODEL,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + "\n" + FORMATO_JSON},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Groq respondió {r.status_code}: {r.text[:200]}")
    try:
        return r.json()["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, ValueError) as e:
        raise RuntimeError(f"Respuesta inesperada de Groq: {e}")


def generate_diet(*, client: dict, target: dict, aliments: list, extra: Optional[str] = None) -> dict:
    """Pide el plan al proveedor configurado y devuelve el objeto ya parseado.

    Los totales no se toman de aquí: quien llama los recalcula con la base de
    datos, así que un plan con cantidades raras se detecta después.
    """
    import json

    prompt = build_prompt(client=client, target=target, aliments=aliments)
    if extra:
        prompt += f"\n\n## Indicaciones del coach\n{extra}"

    texto = _preguntar_groq(prompt) if _proveedor() == "groq" else _preguntar_anthropic(prompt)
    if not texto:
        raise RuntimeError("La IA no devolvió ningún plan.")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"La IA no devolvió JSON válido: {e}")
    if not isinstance(datos, dict):
        raise RuntimeError("La IA no devolvió un objeto JSON.")
    return datos
