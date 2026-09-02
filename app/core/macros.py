"""Cuánto aporta una cantidad de un alimento.

La fórmula estaba copiada en unos cuarenta sitios entre el backend y las
pantallas, y todas dividían entre 100 a ciegas. Pero no todos los alimentos
vienen por 100 g: un huevo grande son 74 kcal por UNIDAD, un cacito de proteína
117 kcal por 29 g, un yogur griego 176 kcal por el envase de 125 g.

Con el divisor fijo, el coach que ponía dos huevos en una dieta veía 1,5 kcal
en vez de 148, y el yogur contaba 220 en vez de 176. Fallaba en las dos
direcciones y el total de la dieta descuadraba sin que nadie supiera por qué.

El dato que hace falta ya estaba guardado —`aliments.quantity` dice a qué
cantidad se refieren esos macros—; lo único que pasaba es que nadie lo miraba.
"""
from typing import Optional


def porcion_de(aliment) -> float:
    """La cantidad a la que se refieren los macros de este alimento.

    Sin dato, 100: es lo que la aplicación ha hecho siempre y lo que vale para
    la enorme mayoría del catálogo. Un cero se trata igual que un vacío, que si
    no la división revienta la pantalla entera por un alimento mal metido.
    """
    q = getattr(aliment, "quantity", None) if aliment is not None else None
    try:
        q = float(q)
    except (TypeError, ValueError):
        return 100.0
    return q if q > 0 else 100.0


def escalar(valor: Optional[float], aliment, cantidad: Optional[float]) -> float:
    """Lo que aportan `cantidad` unidades de este alimento.

    `valor` es el macro tal como está guardado (kcal, proteínas…), referido a
    la porción del alimento.
    """
    if valor is None or cantidad is None:
        return 0.0
    try:
        return float(valor) / porcion_de(aliment) * float(cantidad)
    except (TypeError, ValueError):
        return 0.0


# La misma unidad viene escrita de varias formas según de dónde salga el
# alimento: el catálogo guarda `g`, los ficheros del cliente traían `gr`, y los
# alimentos antiguos la llevan en la relación `quantity_type` con la etiqueta
# larga ("Unidad"). Son la misma cosa. Es el gemelo de `unidadDe` en
# `frontend/js/macros-alimento.js`.
_ALIAS = {
    "g": "g", "gr": "g", "gramo": "g", "gramos": "g",
    "ud": "ud", "u": "ud", "uds": "ud", "unidad": "ud", "unidades": "ud",
    "tz": "ud", "taza": "ud",
    "ml": "ml", "mililitro": "ml", "mililitros": "ml",
    "l": "l", "litro": "l", "kg": "kg", "oz": "oz",
}


def unidad_de(aliment) -> str:
    """La unidad de un alimento, para ENSEÑARLA.

    Sin esto cada pantalla la deducía por su cuenta y el PDF ponía "g" a todo:
    un huevo salía como "2 g" con las kcal de dos unidades enteras. Se mira
    primero `quantity_type`, que es donde la tienen los alimentos antiguos, y
    luego `quantity_unit`, que es donde la guarda el catálogo.
    """
    if aliment is None:
        return "g"
    qt = getattr(aliment, "quantity_type", None)
    texto = None
    if qt is not None:
        texto = getattr(qt, "description", None) or getattr(qt, "name", None)
    if not texto:
        texto = getattr(aliment, "quantity_unit", None)
    u = str(texto or "").strip().lower()
    if not u:
        return "g"
    return _ALIAS.get(u, u)
