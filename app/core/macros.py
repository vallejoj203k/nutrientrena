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
