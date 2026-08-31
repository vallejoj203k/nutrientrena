"""El momento sugerido y la casilla "usar al generar dietas", al importar.

Dos vocabularios que nadie traducía. La pantalla guarda claves cortas
—`desayuno`, `snack`, `principal`—, que son las que comparan los tres chips del
formulario; los ficheros del cliente traen las etiquetas que se leen en
pantalla. Importando las etiquetas tal cual el dato ENTRA en la base, pero el
formulario sale con los chips en blanco: parece que el alimento no tiene
momento cuando sí lo tiene. Es la peor clase de fallo — no hay error, solo un
dato que no se ve.

Y una columna de sí/no leída con `bool(texto)` da True para la cadena
"False": marcaría para el generador los 160 alimentos que el cliente dejó
fuera a propósito.

Aparte, lo que el cliente marcó como crítico: una celda vacía es SIN DATO, no
un cero. La ficha del alimento pinta una rayita cuando no hay dato, así que un
cero inventado se lee como "este alimento no tiene vitamina D", que es una
afirmación que nadie ha hecho.
"""
import io
import uuid

import pytest

from app.core.momentos import booleano, momentos_a_claves, texto_de_momentos
from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment, AlimentDescription

CABECERA = ("Nombre,Grupo de alimento,Marca,Cantidad,Unidad,Calorias,Proteinas,"
            "Carbohidratos,Grasas,Fibra,vitA,vitD,calcium,"
            "momento_sugerido,usar_en_generador\n")


def _subir(client, headers, filas):
    csv = CABECERA + "".join(filas)
    return client.post("/api/aliments/import", headers=headers,
                       files={"file": ("base.csv", io.BytesIO(csv.encode()), "text/csv")})


def _buscar(nombre_like):
    db = SessionLocal()
    try:
        return db.query(Aliment).filter(Aliment.name.like(nombre_like)).first()
    finally:
        db.close()


# ── El vocabulario de los momentos ─────────────────────────────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("Desayuno", "desayuno"),
    ("Media mañana / merienda", "snack"),
    ("Comida / cena", "principal"),
    ("Desayuno, Media mañana / merienda", "desayuno,snack"),
    ("Desayuno, Comida / cena", "desayuno,principal"),
    ("Media mañana / merienda, Comida / cena", "snack,principal"),
    # Vacío = vale para los tres. Se guarda vacío, no los tres marcados.
    ("", None),
    ("   ", None),
    # Y lo que ya está guardado tiene que seguir entrando igual: por la pantalla
    # de importar puede volver un CSV que exportó la propia plataforma.
    ("desayuno,principal", "desayuno,principal"),
])
def test_LOS_MOMENTOS_DEL_FICHERO_SE_TRADUCEN_A_LAS_CLAVES(texto, esperado):
    assert momentos_a_claves(texto) == esperado


def test_el_orden_no_depende_de_como_venga_escrito():
    """El mismo alimento guardado de dos formas distintas según el orden del
    fichero sería el mismo dato con dos caras."""
    assert momentos_a_claves("Comida / cena, Desayuno") == "desayuno,principal"
    assert momentos_a_claves("Desayuno, Comida / cena") == "desayuno,principal"


def test_un_momento_que_no_existe_se_ignora_sin_tumbar_la_fila():
    """Mejor un alimento sin momento que una importación cortada a la mitad."""
    assert momentos_a_claves("Cena tardía") is None
    assert momentos_a_claves("Desayuno, Vete a saber") == "desayuno"


def test_lo_guardado_se_vuelve_a_leer_como_lo_escribio_el_cliente():
    assert texto_de_momentos("desayuno,snack") == "Desayuno, Media mañana / merienda"
    assert texto_de_momentos(None) == ""


# ── La casilla de sí/no ────────────────────────────────────────────────────

def test_LA_CADENA_FALSE_NO_ES_VERDADERA():
    """`bool("False")` es True. Con ese fallo, los 160 alimentos que el cliente
    dejó fuera del generador entrarían igualmente."""
    assert booleano("False") is False
    assert booleano("false") is False
    assert booleano("True") is True
    assert booleano("0") is False
    assert booleano("1") is True


def test_SOLO_UN_NO_ESCRITO_CUENTA_COMO_NO():
    """Ni una celda vacía ni una columna ausente son una respuesta. Tomarlas
    por un no dejaría fuera del generador alimentos sobre los que nadie se ha
    pronunciado — y eso no se nota: simplemente no se proponen nunca."""
    assert booleano(None, por_defecto=True) is True      # la columna no viene
    assert booleano("", por_defecto=True) is True        # la celda está vacía
    assert booleano("False", por_defecto=True) is False  # esto sí es un no


# ── Y por el camino real: el importador de la pantalla ─────────────────────

def test_EL_MOMENTO_LLEGA_EN_EL_IDIOMA_DE_LOS_CHIPS(client, seed, admin_headers):
    """Si llegara la etiqueta larga, el chip del formulario no se marcaría y el
    coach vería el alimento como si no tuviera momento."""
    suf = uuid.uuid4().hex[:8]
    r = _subir(client, admin_headers, [
        f"Tostada {suf},Cereales {suf},,100,gr,250,8,45,3,,,,,\"Desayuno, Comida / cena\",True\n"])
    assert r.status_code == 200, r.text
    assert _buscar(f"Tostada {suf}%").meal_moments == "desayuno,principal"


def test_la_casilla_del_generador_se_guarda(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"Dentro {suf},Otros {suf},,100,gr,100,1,1,1,,,,,Comida / cena,True\n",
        f"Fuera {suf},Otros {suf},,100,gr,100,1,1,1,,,,,Comida / cena,False\n"])
    assert _buscar(f"Dentro {suf}%").use_in_generator is True
    assert _buscar(f"Fuera {suf}%").use_in_generator is False


def test_UNA_CELDA_VACIA_ES_SIN_DATO_NO_UN_CERO(client, seed, admin_headers):
    """Lo que el cliente marcó como crítico. La ficha pinta una rayita cuando
    no hay dato; un cero inventado dice "este alimento no tiene vitamina D",
    que es una afirmación que nadie ha hecho.
    """
    suf = uuid.uuid4().hex[:8]
    # vitA vacía, vitD con un cero ESCRITO. Son cosas distintas.
    _subir(client, admin_headers, [
        f"Mixto {suf},Otros {suf},,100,gr,100,1,1,1,,,0,120,,True\n"])
    al = _buscar(f"Mixto {suf}%")

    db = SessionLocal()
    try:
        d = db.query(AlimentDescription).filter(
            AlimentDescription.aliment_id == al.id).first()
        assert d is not None, "no se han guardado los micronutrientes"
        assert d.vita is None, "una celda vacía se ha guardado como un número"
        assert d.vitd == 0, "un cero escrito a mano se ha perdido"
        assert d.calcium == 120
    finally:
        db.close()


def test_un_macro_vacio_tambien_queda_sin_dato(client, seed, admin_headers):
    """Mismo criterio arriba: unas calorías vacías no son cero calorías."""
    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"Sinkcal {suf},Otros {suf},,100,gr,,1,1,1,,,,,,True\n"])
    al = _buscar(f"Sinkcal {suf}%")
    assert al.calories is None, al.calories
    assert al.proteins == 1


# ── Y que el generador haga caso a la casilla ──────────────────────────────

def test_EL_GENERADOR_SOLO_USA_LOS_MARCADOS(client, seed, admin_headers):
    """La casilla no vale de nada si el generador la ignora. El cliente dejó
    160 alimentos fuera a propósito: proponerlos igualmente sería tirar por
    tierra el trabajo de revisar el catálogo uno a uno.
    """
    from app.routers.nutrition.diets import _catalogo_generador

    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"Genera {suf},Otros {suf},,100,gr,100,10,5,2,,,,,Comida / cena,True\n",
        f"Nogenera {suf},Otros {suf},,100,gr,100,10,5,2,,,,,Comida / cena,False\n"])

    db = SessionLocal()
    try:
        class _SinOrg:
            org_id = None
            solo_plataforma = False
        nombres = [a.name for a in _catalogo_generador(db, _SinOrg()).all()]

        assert f"Genera {suf}" in nombres, "no propone uno que sí está marcado"
        assert f"Nogenera {suf}" not in nombres, \
            "propone un alimento que el cliente dejó fuera del generador"
    finally:
        db.close()
