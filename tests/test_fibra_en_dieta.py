"""La fibra de cada alimento, en el editor de dietas.

Salía 0 g en todos —fresas, anacardos, muesli— aunque el catálogo la tuviera.
Tres cosas se juntaban:

  · La fibra vive en la ficha de micronutrientes (`aliment_descriptions`),
    no junto a los macros, y las pantallas la leían de `a.fiber`: nada.
  · Meter un alimento en una dieta hace una COPIA suya, y la copia no llevaba
    la ficha. Aunque se hubiera leído bien, la copia no tenía nada que leer.
  · Y las copias que ya existen tampoco: hay que dársela.

Lo que hay que dejar sujeto:

  · Que el buscador y la dieta digan la fibra del alimento.
  · Que la copia lleve la ficha ENTERA, no solo la fibra: el sodio o el hierro
    del alimento se pierden igual al copiarlo.
  · Que la reparación de las copias viejas no pise una ficha que ya existía.
  · Y que un alimento sin ficha siga sin inventarse nada.
"""
import importlib.util
import os
import uuid

from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models.nutrition.aliment import Aliment, AlimentDescription

from tests.test_macros_porcion import _monta


def _alimento(client, h, nombre, fibra=None, **micros):
    body = {"name": nombre, "calories": 40, "proteins": 0.7, "carbohydrates": 7,
            "fats": 0.5, "quantity": 100, "quantity_unit": "g"}
    if fibra is not None or micros:
        body["description"] = {"fiber": fibra, **micros}
    r = client.post("/api/aliments", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _dieta_con(client, h, suf, aliment_id, cantidad=100):
    r = client.post("/api/diets", headers=h, json={
        "title": f"Dieta {suf}",
        "foods": [{"name": "Desayuno", "time": "08:00", "detail": [
            {"aliment_id": aliment_id, "quantity_calc": cantidad, "order": 0}]}]})
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _copia_de(dieta):
    return dieta["foods"][0]["detail"][0]


def _ficha(aliment_id):
    db = SessionLocal()
    try:
        return db.query(AlimentDescription).filter(
            AlimentDescription.aliment_id == aliment_id).first()
    finally:
        db.close()


# ── Leerla ─────────────────────────────────────────────────────────────────

def test_el_buscador_dice_la_fibra(client, seed, admin_headers):
    """Es lo que el editor guarda al elegir un alimento del desplegable."""
    suf = uuid.uuid4().hex[:8]
    h, _d, _hc = _monta(client, admin_headers, suf)
    _alimento(client, h, f"Fresa {suf}", fibra=2.2)

    r = client.get(f"/api/aliments/search?search=Fresa {suf}", headers=h)
    assert r.status_code == 200, r.text
    hallados = r.json()["data"]["data"]
    assert hallados and hallados[0]["fiber"] == 2.2, hallados


def test_LA_DIETA_DICE_LA_FIBRA_DEL_ALIMENTO(client, seed, admin_headers):
    """El caso de la captura: fresas con 0 g."""
    suf = uuid.uuid4().hex[:8]
    h, _d, _hc = _monta(client, admin_headers, suf)
    fresa = _alimento(client, h, f"Fresa {suf}", fibra=2.2)
    dieta = _dieta_con(client, h, suf, fresa)

    assert _copia_de(dieta)["aliment"]["fiber"] == 2.2, _copia_de(dieta)

    # Y al volver a abrirla, igual: no era solo la respuesta de crearla.
    otra_vez = client.get(f"/api/diets/{dieta['id']}/edit", headers=h).json()["data"]
    assert _copia_de(otra_vez)["aliment"]["fiber"] == 2.2


def test_un_alimento_sin_ficha_no_se_inventa_fibra(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _d, _hc = _monta(client, admin_headers, suf)
    dieta = _dieta_con(client, h, suf, _alimento(client, h, f"Agua {suf}"))
    assert _copia_de(dieta)["aliment"]["fiber"] is None


# ── La copia lleva la ficha entera ─────────────────────────────────────────

def test_LA_COPIA_LLEVA_LA_FICHA_ENTERA_NO_SOLO_LA_FIBRA(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _d, _hc = _monta(client, admin_headers, suf)
    original = _alimento(client, h, f"Anacardo {suf}", fibra=3.3, sodium=12, iron=6.7)
    dieta = _dieta_con(client, h, suf, original)
    copia = _copia_de(dieta)["aliment_id"]

    assert copia != original, "la dieta apunta al catálogo, no a una copia"
    ficha = _ficha(copia)
    assert ficha is not None, "la copia no lleva ficha de micros"
    assert (ficha.fiber, ficha.sodium, ficha.iron) == (3.3, 12, 6.7)


def test_la_ficha_de_la_copia_es_suya_no_la_del_catalogo(client, seed, admin_headers):
    """Editar el catálogo no cambia las dietas ya montadas; con la ficha
    tiene que pasar lo mismo, si no la fibra de una dieta cambiaría sola."""
    suf = uuid.uuid4().hex[:8]
    h, _d, _hc = _monta(client, admin_headers, suf)
    original = _alimento(client, h, f"Muesli {suf}", fibra=8.0)
    dieta = _dieta_con(client, h, suf, original)

    r = client.put(f"/api/aliments/{original}/update", headers=h, json={"description": {"fiber": 1.0}})
    assert r.status_code == 200, r.text
    assert _ficha(original).fiber == 1.0
    assert _ficha(_copia_de(dieta)["aliment_id"]).fiber == 8.0


# ── Las copias que ya existían ─────────────────────────────────────────────

def _migracion():
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "alembic", "versions", "c5d6e7f8a901_micros_a_los_clones.py")
    spec = importlib.util.spec_from_file_location("mig_micros", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _copia_vieja(original_id, con_ficha=None):
    """Una copia como las que hay en la base: sin ficha (o con una propia)."""
    db = SessionLocal()
    try:
        src = db.query(Aliment).get(original_id)
        c = Aliment(name=src.name, calories=src.calories, quantity=100,
                    parent_id=src.id)
        if con_ficha is not None:
            c.description = AlimentDescription(fiber=con_ficha)
        db.add(c)
        db.commit()
        return c.id
    finally:
        db.close()


def test_LAS_COPIAS_VIEJAS_RECIBEN_LA_FICHA_DE_SU_PADRE(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _d, _hc = _monta(client, admin_headers, suf)
    original = _alimento(client, h, f"Lenteja {suf}", fibra=10.6, iron=4.7)
    sin_ficha = _copia_vieja(original)
    con_ficha = _copia_vieja(original, con_ficha=5.0)
    assert _ficha(sin_ficha) is None

    with engine.begin() as conn:
        _migracion().copiar_micros_a_los_clones(conn)

    f = _ficha(sin_ficha)
    assert f is not None and (f.fiber, f.iron) == (10.6, 4.7), f
    assert _ficha(con_ficha).fiber == 5.0, "ha pisado una ficha que ya existía"
    # Y el original sigue con una sola ficha, la suya.
    db = SessionLocal()
    try:
        n = db.execute(text("SELECT COUNT(*) FROM aliment_descriptions WHERE aliment_id = :i"),
                       {"i": original}).scalar()
    finally:
        db.close()
    assert n == 1


def test_la_reparacion_se_puede_repetir_sin_duplicar(client, seed, admin_headers):
    """`start.sh` corre las migraciones en cada despliegue; una segunda pasada
    no puede dejar dos fichas en la misma copia."""
    suf = uuid.uuid4().hex[:8]
    h, _d, _hc = _monta(client, admin_headers, suf)
    original = _alimento(client, h, f"Avena {suf}", fibra=9.0)
    copia = _copia_vieja(original)
    with engine.begin() as conn:
        _migracion().copiar_micros_a_los_clones(conn)
        _migracion().copiar_micros_a_los_clones(conn)
    db = SessionLocal()
    try:
        n = db.execute(text("SELECT COUNT(*) FROM aliment_descriptions WHERE aliment_id = :i"),
                       {"i": copia}).scalar()
    finally:
        db.close()
    assert n == 1, n
