"""Generación de dietas con IA (Claude).

El modelo NO inventa alimentos ni hace las cuentas: se le entrega el catálogo
real de alimentos del coach y los objetivos ya calculados en la sección de
Nutrición, y solo decide qué alimentos usar y en qué cantidad. Los totales se
recalculan después con los valores de la base de datos, de modo que lo que ve
el coach siempre cuadra con los cálculos de la aplicación.
"""
from typing import Optional

from app.config import settings

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


def ai_enabled() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


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


def generate_diet(*, client: dict, target: dict, aliments: list, extra: Optional[str] = None) -> dict:
    """Pide el plan a Claude y devuelve el objeto ya validado contra el esquema."""
    import anthropic

    api = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = build_prompt(client=client, target=target, aliments=aliments)
    if extra:
        prompt += f"\n\n## Indicaciones del coach\n{extra}"

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

    import json

    texto = next((b.text for b in message.content if b.type == "text"), "")
    if not texto:
        raise RuntimeError("La IA no devolvió ningún plan.")
    return json.loads(texto)
