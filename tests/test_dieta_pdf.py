"""El PDF de la dieta: el papel que el cliente se lleva a la cocina.

Rehecho para que se vea como el diseño, y al hacerlo salieron tres cuentas
mal. Importan más que el aspecto, porque un PDF impreso no tiene quien lo
desmienta: el cliente no compara con la pantalla, hace la compra con él.

  · Las kcal de cada comida sumaban `aliment.calories` A PELO — el valor por
    100 g, sin mirar cuántos gramos había. Un desayuno de 80 g de avena y 20 g
    de almendras se iba a 968 kcal en vez de 463.
  · Los macros de la cabecera salían de lo que se escribió al crear la dieta.
    Si un alimento cambia de cantidad, las kcal se mueven y ellos no.
  · Y la cantidad ponía "g" a todo: dos huevos salían como "2 g" con las kcal
    de dos unidades enteras.

Las comprobaciones leen el texto DE DENTRO del PDF. Mirar solo que empieza por
"%PDF" es compatible con una página en blanco.
"""
import base64
import re
import zlib

from app.pdf.diet_pdf import generate_diet_pdf


def _texto(pdf):
    """El texto que hay dentro del PDF (ASCII85 sobre zlib, como lo deja
    reportlab). Los dos vienen en la biblioteca estándar."""
    partes = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        d = m.group(1).strip()
        try:
            d = base64.a85decode(d, adobe=True, ignorechars=b" \t\r\n")
        except Exception:
            pass
        try:
            partes.append(zlib.decompress(d))
        except Exception:
            partes.append(d)
    return b"".join(partes).decode("latin-1")


class _O:
    def __init__(self, **k):
        self.__dict__.update(k)


def _al(nombre, kcal, p=0, c=0, g=0, cantidad=100, unidad="g"):
    return _O(name=nombre, calories=kcal, proteins=p, carbohydrates=c, fats=g,
              quantity=cantidad, quantity_unit=unidad, quantity_type=None)


def _dieta(**k):
    base = dict(
        title="Recomposicion", user=None, detail=None,
        type=_O(description="Equilibrada"),
        # A propósito EQUIVOCADO: el PDF tiene que sumar las comidas, no
        # creerse este número.
        calories=9999, foods=[],
    )
    base.update(k)
    return _O(**base)


# 80 g de avena (389/100 g) = 311,2 y 20 g de almendras (579/100 g) = 115,8.
DESAYUNO = _O(name="Desayuno", time="08:00:00", subtitle=None, detail=[
    _O(quantity=80, subtitle=None, aliment=_al("Avena", 389, 16.9, 66.3, 6.9)),
    _O(quantity=20, subtitle="crudas", aliment=_al("Almendras", 579, 21, 22, 50)),
])
# Dos huevos grandes: 74 kcal por UNIDAD.
COMIDA = _O(name="Comida", time="14:00:00", subtitle=None, detail=[
    _O(quantity=2, subtitle=None, aliment=_al("Huevo Grande (L)", 74, 6.3, 0.4, 5,
                                              cantidad=1, unidad="ud")),
])


# ── Que salga un PDF ───────────────────────────────────────────────────────

def test_sale_un_pdf_de_verdad():
    pdf = generate_diet_pdf(_dieta(foods=[DESAYUNO]))
    assert pdf.startswith(b"%PDF"), pdf[:20]
    assert len(pdf) > 1500, len(pdf)


def test_lleva_lo_que_se_lee_en_la_cabecera():
    txt = _texto(generate_diet_pdf(_dieta(foods=[DESAYUNO])))
    assert "PLAN DE ALIMENTACI" in txt, txt[:400]
    assert "Recomposicion" in txt
    assert "Equilibrada" in txt
    for etiqueta in ("CALOR", "PROTE", "CARBOHIDRATOS", "GRASAS"):
        assert etiqueta in txt, f"falta {etiqueta}"
    assert "INGREDIENTE" in txt and "CANTIDAD" in txt


# ── Las cuentas ────────────────────────────────────────────────────────────

def test_LAS_KCAL_DE_LA_COMIDA_VAN_POR_LA_PORCION():
    """311,2 + 115,8 = 427. Sumando `calories` a pelo saldrían 968, que es la
    suma de dos valores "por 100 g" de cantidades que no son 100 g."""
    txt = _texto(generate_diet_pdf(_dieta(foods=[DESAYUNO])))
    assert "427 kcal" in txt, [t for t in txt.split() if "kcal" in t][:6]
    assert "968" not in txt, "sigue sumando el valor por 100 g a pelo"


def test_LA_CABECERA_SUMA_LAS_COMIDAS_NO_SE_CREE_LA_DIETA():
    """La dieta dice 9999 kcal. El PDF tiene que decir lo que hay en el plato."""
    txt = _texto(generate_diet_pdf(_dieta(foods=[DESAYUNO, COMIDA])))
    assert "9999" not in txt, "se ha creído las kcal escritas en la dieta"
    # 427 del desayuno + 148 de los dos huevos = 575.
    assert "575" in txt, txt[:600]


def test_los_macros_tambien_se_suman():
    """Antes salían de `diet.detail`, que es lo que se escribió al crear la
    dieta. Aquí `detail` trae números disparatados a propósito."""
    d = _dieta(foods=[DESAYUNO],
               detail=_O(proteins=777, carbs=888, fats=999,
                         weight=None, height=None, age=None, body_fat=None))
    txt = _texto(generate_diet_pdf(d))
    for inventado in ("777", "888", "999"):
        assert inventado not in txt, f"ha usado {inventado} de la dieta en vez de sumar"
    # Proteínas: 16,9×0,8 + 21×0,2 = 17,72 → 18.
    assert "18" in txt


def test_LA_CANTIDAD_LLEVA_SU_UNIDAD():
    """Dos huevos son "2 ud", no "2 g". Con "g" el papel dice que hay que
    pesar dos gramos de huevo."""
    txt = _texto(generate_diet_pdf(_dieta(foods=[COMIDA])))
    assert "2 ud" in txt, txt[:600]
    assert "2 g" not in txt


def test_la_cantidad_no_arrastra_un_decimal_de_mas():
    """80.0 en el papel se lee como una precisión que nadie ha medido."""
    txt = _texto(generate_diet_pdf(_dieta(foods=[DESAYUNO])))
    assert "80 g" in txt and "80.0" not in txt, txt[:400]


# ── Lo que no puede tumbarlo ───────────────────────────────────────────────

def test_UN_NOMBRE_CON_SIGNOS_NO_DESAPARECE():
    """Reportlab lee `< >` como etiquetas suyas: sin escapar, el alimento no
    sale mal, DESAPARECE, y el PDF se entrega con una línea menos."""
    comida = _O(name="Cena", time=None, subtitle=None, detail=[
        _O(quantity=100, subtitle=None, aliment=_al("Yogur <2% MG> & nueces", 60)),
    ])
    txt = _texto(generate_diet_pdf(_dieta(foods=[comida])))
    assert "Yogur" in txt and "MG" in txt, "se ha perdido el alimento entero"


def test_una_dieta_sin_comidas_no_revienta():
    pdf = generate_diet_pdf(_dieta(foods=[]))
    assert pdf.startswith(b"%PDF")
    txt = _texto(pdf)
    assert "Recomposicion" in txt


def test_una_comida_sin_alimentos_lo_dice():
    vacia = _O(name="Cena", time=None, subtitle=None, detail=[])
    txt = _texto(generate_diet_pdf(_dieta(foods=[vacia])))
    assert "Sin alimentos" in txt, txt[:500]


def test_un_alimento_sin_datos_no_para_el_pdf():
    """Una fila a medias no puede costar el documento entero."""
    rara = _O(name="Merienda", time=None, subtitle=None, detail=[
        _O(quantity=None, subtitle=None, aliment=_al("Sin cantidad", None)),
        _O(quantity=50, subtitle=None, aliment=None),
    ])
    pdf = generate_diet_pdf(_dieta(foods=[rara]))
    assert pdf.startswith(b"%PDF")
    assert "Sin cantidad" in _texto(pdf)
