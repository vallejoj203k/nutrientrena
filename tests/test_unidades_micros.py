"""Las unidades de los micronutrientes en el formulario de alimentos.

Seis micronutrientes se guardan en MICROGRAMOS y el formulario los etiquetaba
en miligramos: vitaminas A, B9, B12, D, K y selenio. La ficha del alimento ya
los mostraba bien, así que la misma cifra se leía con dos unidades distintas
según la pantalla — y quien rellenaba el formulario metía un número mil veces
mayor del que creía.

Lo que hace frágil a este arreglo: el formulario está COPIADO en cuatro
páginas. Cambiar una y olvidar las otras deja el fallo en tres sitios, y no hay
nada que avise. Estas pruebas leen el HTML de las cuatro y lo contrastan con la
tabla de unidades que ya usaba la vista de detalle, que es la referencia.

No se comprueba ningún valor guardado: los datos ya estaban en microgramos y no
se ha convertido nada.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent / "frontend"

# Los que van en microgramos. Es la misma lista que MICRO_UNITS declara en
# aliments.html para la vista de detalle.
EN_MICROGRAMOS = ["vita", "vitb9", "vitb12", "vitd", "vitk", "selenium"]

# El resto de vitaminas y minerales, que sí van en miligramos.
EN_MILIGRAMOS = ["vitb1", "vitb2", "vitb3", "vitb5", "vitb6", "vitc", "vite",
                 "calcium", "iron", "magnesium", "phosphorus", "potassium",
                 "sodium", "zinc", "copper", "manganese"]

# Cada página escribe los `id` con su propio prefijo.
PAGINAS = {
    "aliments.html": "f{Clave}",
    "nutrition-catalog.html": "al_f{Clave}",
    "diets.html": "ca_{clave}",
    "recipes.html": "ca_{clave}",
}


def _id(patron, clave):
    return patron.format(clave=clave, Clave=clave[0].upper() + clave[1:])


def _unidad(html, ident):
    """La unidad escrita junto a ese campo, o None si no está el campo."""
    m = re.search(r'<input id="' + re.escape(ident) + r'"[^>]*/>\s*<span>([^<]*)</span>', html)
    return m.group(1).strip() if m else None


@pytest.mark.parametrize("pagina,patron", sorted(PAGINAS.items()))
def test_LOS_SEIS_MICROS_EN_MICROGRAMOS_DICEN_MCG(pagina, patron):
    """El fallo reportado. Con `mg` puesto, quien rellena el formulario mete un
    número mil veces mayor del que cree."""
    html = (RAIZ / pagina).read_text(encoding="utf-8")
    mal = {}
    for clave in EN_MICROGRAMOS:
        ident = _id(patron, clave)
        u = _unidad(html, ident)
        assert u is not None, f"{pagina}: no está el campo {ident}"
        if u != "mcg":
            mal[ident] = u
    assert not mal, f"{pagina}: etiquetados en la unidad equivocada -> {mal}"


@pytest.mark.parametrize("pagina,patron", sorted(PAGINAS.items()))
def test_los_demas_siguen_en_miligramos(pagina, patron):
    """Cambiar de más es tan malo como cambiar de menos: el calcio y el hierro
    van en miligramos y tienen que seguir diciéndolo."""
    html = (RAIZ / pagina).read_text(encoding="utf-8")
    mal = {}
    for clave in EN_MILIGRAMOS:
        ident = _id(patron, clave)
        u = _unidad(html, ident)
        if u is not None and u != "mg":
            mal[ident] = u
    assert not mal, f"{pagina}: no deberían haber cambiado -> {mal}"


def test_EL_FORMULARIO_DICE_LO_MISMO_QUE_LA_FICHA_DEL_ALIMENTO():
    """La referencia no es esta prueba: es `MICRO_UNITS`, la tabla que usa la
    vista de detalle. El fallo fue justamente que el formulario y la ficha
    decían cosas distintas de la misma cifra, así que se comprueba contra ella
    y no contra una lista escrita aquí a mano.
    """
    html = (RAIZ / "aliments.html").read_text(encoding="utf-8")
    bloque = re.search(r"const MICRO_UNITS = \{(.*?)\};", html, re.S)
    assert bloque, "ya no existe MICRO_UNITS: esta prueba mide otra cosa"
    segun_la_ficha = dict(re.findall(r"(\w+)\s*:\s*'(\w+)'", bloque.group(1)))

    for clave in EN_MICROGRAMOS:
        assert segun_la_ficha.get(clave) == "mcg", \
            f"la ficha ya no dice mcg de {clave}: {segun_la_ficha.get(clave)}"

    for pagina, patron in PAGINAS.items():
        h = (RAIZ / pagina).read_text(encoding="utf-8")
        for clave, unidad in segun_la_ficha.items():
            if unidad not in ("mcg", "mg"):
                continue          # gramos: fibra, grasas, agua — otro bloque
            u = _unidad(h, _id(patron, clave))
            if u is None:
                continue          # esa página no tiene ese campo
            assert u == unidad, \
                (f"{pagina}: {clave} sale como «{u}» en el formulario y como "
                 f"«{unidad}» en la ficha del alimento")
