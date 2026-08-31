"""Importar el catálogo de alimentos desde la propia plataforma.

El cliente no tiene el proyecto en su ordenador: trabaja desde Railway y el
navegador. Así que la carga tiene que poder hacerse desde la pantalla de
Alimentos, subiendo el CSV, sin instalar nada.

El importador ya existía pero solo entendía su propio formato. El CSV que llega
trae la categoría por NOMBRE ("Frutas") y no por número, la unidad como `gr`,
los nombres en minúscula y algunos repetidos. Sin esto:

  · los 89 alimentos de "Frutas" entraban sin agrupar, y la biblioteca sale
    como una lista plana de ochocientos nombres;
  · `gr` no es la unidad que usa la plataforma;
  · y los repetidos entraban dos veces.
"""
import io
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment, AlimentDescription
from app.models.nutrition.group_food import GroupFood

from tests.test_org_scope import _crear_usuario

CABECERA = ("id,Nombre,Grupo de alimento,Marca,Cantidad,Unidad,Calorias,Proteinas,"
            "Carbohidratos,Grasas,Fibra,calcium,iron,choline,saturatedFat,"
            "tiene_micros,es_duplicado,momento_sugerido,comments\n")


def _subir(client, headers, filas):
    csv = CABECERA + "".join(filas)
    return client.post("/api/aliments/import", headers=headers,
                       files={"file": ("catalogo.csv", io.BytesIO(csv.encode()), "text/csv")})


def _buscar(nombre_like):
    db = SessionLocal()
    try:
        return db.query(Aliment).filter(Aliment.name.like(nombre_like)).first()
    finally:
        db.close()


# ── La categoría, que es lo que ordena la biblioteca ───────────────────────

def test_LA_CATEGORIA_ENTRA_POR_SU_NOMBRE_no_por_un_numero(client, seed, admin_headers):
    """Nadie que prepare un CSV a mano sabe qué id tiene "Frutas"."""
    suf = uuid.uuid4().hex[:8]
    r = _subir(client, admin_headers, [
        f"1,Manzana {suf},Frutas {suf},,100,gr,52,0.3,14,0.2,2.4,6,0.1,,,False,False,,\n"])
    assert r.status_code == 200, r.text
    assert r.json()["data"]["created"] == 1, r.json()

    al = _buscar(f"Manzana {suf}%")
    assert al is not None and al.group_food_id is not None, al
    db = SessionLocal()
    try:
        assert db.query(GroupFood).filter(GroupFood.id == al.group_food_id).first().name \
            == f"Frutas {suf}"
    finally:
        db.close()


def test_una_categoria_que_ya_existe_no_se_duplica(client, seed, admin_headers):
    """Si no, la biblioteca sale con dos secciones que se llaman igual."""
    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"1,Pera {suf},Frutas {suf},,100,gr,57,0.4,15,0.1,,,,,,False,False,,\n"])
    _subir(client, admin_headers, [
        f"2,Uva {suf},Frutas {suf},,100,gr,69,0.7,18,0.2,,,,,,False,False,,\n"])

    db = SessionLocal()
    try:
        assert db.query(GroupFood).filter(GroupFood.name == f"Frutas {suf}").count() == 1
    finally:
        db.close()


# ── Lo que se limpia por el camino ─────────────────────────────────────────

def test_la_unidad_gr_se_guarda_como_g(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"1,Arroz {suf},Cereales {suf},,100,gr,360,7,79,0.6,,,,,,False,False,,\n"])
    assert _buscar(f"Arroz {suf}%").quantity_unit == "g"


def test_una_u_suelta_se_trata_como_unidad(client, seed, admin_headers):
    """El CSV trae 22 filas con `ud` y una con `u`. Son lo mismo."""
    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"1,Centrum {suf},Suplementos {suf},,1,u,0,0,0,0,,,,,,False,False,,\n"])
    assert _buscar(f"Centrum {suf}%").quantity_unit == "ud"


def test_los_nombres_en_minuscula_se_arreglan(client, seed, admin_headers):
    """120 filas vienen así y quedan como un renglón desordenado entre cientos."""
    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"1,alitas de pollo {suf},Aves {suf},,100,gr,203,18,0,14,,,,,,False,False,,\n"])
    assert _buscar(f"Alitas de pollo {suf}%") is not None


def test_UN_REPETIDO_EN_EL_MISMO_FICHERO_NO_ENTRA_DOS_VECES(client, seed, admin_headers):
    """El CSV trae 19 nombres por duplicado. Sin esto, la biblioteca sale con
    "Almendras" dos veces y el coach no sabe cuál coger."""
    suf = uuid.uuid4().hex[:8]
    r = _subir(client, admin_headers, [
        f"1,Almendras {suf},Frutos secos {suf},,100,gr,616,21,21,50,12.5,269,3.7,,,True,True,,\n",
        f"2,Almendras {suf},Frutos secos {suf},,100,gr,600,20,20,49,,,,,,False,True,,\n"])
    assert r.status_code == 200, r.text
    assert r.json()["data"]["created"] == 1, r.json()["data"]
    assert any("ya venía antes" in e for e in r.json()["data"]["errors"]), r.json()["data"]

    db = SessionLocal()
    try:
        assert db.query(Aliment).filter(Aliment.name == f"Almendras {suf}").count() == 1
    finally:
        db.close()


# ── Lo que ya funcionaba, que no se rompe ──────────────────────────────────

def test_los_micronutrientes_siguen_entrando(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"1,Avena {suf},Cereales {suf},Hacendado,100,gr,389,16.9,66.3,6.9,10.6,54,4.7,,1.2,True,False,Desayuno,\n"])
    al = _buscar(f"Avena {suf}%")
    assert al.brand == "Hacendado", al.brand
    # Se guarda la CLAVE, no la etiqueta: es la que comparan los tres chips del
    # formulario. Guardando "Desayuno" el dato entra y el chip no se marca.
    assert al.meal_moments == "desayuno", al.meal_moments

    db = SessionLocal()
    try:
        d = db.query(AlimentDescription).filter(AlimentDescription.aliment_id == al.id).first()
        assert d is not None, "no se han guardado los micronutrientes"
        assert d.fiber == 10.6 and d.calcium == 54 and d.iron == 4.7, (d.fiber, d.calcium, d.iron)
        # Cabeceras en inglés y con mayúsculas, tal como vienen del catálogo.
        assert d.saturated_fats == 1.2, d.saturated_fats
    finally:
        db.close()


def test_LA_PORCION_SE_GUARDA_para_que_las_kcal_salgan_bien(client, seed, admin_headers):
    """Un huevo son 74 kcal por UNIDAD. Si la porción no se guardara, la dieta
    volvería a contar 0,74 — el fallo que se acaba de arreglar."""
    suf = uuid.uuid4().hex[:8]
    _subir(client, admin_headers, [
        f"1,Huevo Grande {suf},Huevos {suf},,1,ud,74,6.3,0.4,5.2,,,,,,False,False,,\n"])
    al = _buscar(f"Huevo Grande {suf}%")
    assert al.quantity == 1, al.quantity
    assert al.quantity_unit == "ud", al.quantity_unit

    from app.core.macros import escalar
    assert escalar(al.calories, al, 2) == 148


def test_una_fila_sin_nombre_no_para_la_importacion(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    r = _subir(client, admin_headers, [
        f",,Frutas {suf},,100,gr,50,0,12,0,,,,,,False,False,,\n",
        f"2,Kiwi {suf},Frutas {suf},,100,gr,61,1.1,15,0.5,,,,,,False,False,,\n"])
    assert r.json()["data"]["created"] == 1, r.json()["data"]
    assert _buscar(f"Kiwi {suf}%") is not None


def test_UN_COACH_NO_METE_NADA_EN_EL_CATALOGO_COMUN(client, seed, admin_headers):
    """Lo que importa un coach es suyo. Si entrara en el catálogo común, se lo
    encontrarían todos los demás centros de la plataforma."""
    suf = uuid.uuid4().hex[:8]
    from tests.test_org_scope import _crear_coach, _crear_organizacion
    _u, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.imp.{suf}@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_coach, f"Centro Imp {suf}")

    _subir(client, h_coach, [
        f"1,Suyo {suf},Frutas {suf},,100,gr,50,1,10,0,,,,,,False,False,,\n"])
    al = _buscar(f"Suyo {suf}%")
    assert al.organization_id == org_id, al.organization_id


def test_un_cliente_no_puede_importar(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h_cli = _crear_usuario(
        client, admin_headers, f"cli.imp.{suf}@nutrientrena-qa.com", role_id=6)
    r = _subir(client, h_cli, [
        f"1,Colado {suf},Frutas {suf},,100,gr,50,1,10,0,,,,,,False,False,,\n"])
    assert r.status_code == 403, r.status_code


def test_DE_DOS_REPETIDOS_SE_QUEDA_EL_QUE_TRAE_MICRONUTRIENTES(client, seed, admin_headers):
    """Aunque venga el segundo. La copia sin micronutrientes trae solo macros y
    suele ser la que metió a mano algún cliente; quedarse con esa perdería los
    datos buenos. Mismo criterio que el script de carga masiva: si cada camino
    descartara una distinta, el catálogo saldría diferente según por dónde se
    cargue.
    """
    suf = uuid.uuid4().hex[:8]
    r = _subir(client, admin_headers, [
        f"1,Coco {suf},Frutas {suf},,100,gr,300,3,15,30,,,,,,False,True,,\n",
        f"2,Coco {suf},Frutas {suf},,100,gr,354,3.3,15.2,33.5,9.0,14,2.4,,29.7,True,True,,\n"])
    assert r.status_code == 200, r.text
    assert r.json()["data"]["created"] == 1, r.json()["data"]

    al = _buscar(f"Coco {suf}%")
    assert al.calories == 354, "se ha quedado con la copia sin micronutrientes"
    db = SessionLocal()
    try:
        d = db.query(AlimentDescription).filter(AlimentDescription.aliment_id == al.id).first()
        assert d is not None and d.fiber == 9.0, d
    finally:
        db.close()
