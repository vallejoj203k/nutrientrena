"""Corregir un alimento del catálogo llega a las dietas ya montadas.

Meter un alimento en una dieta guarda una COPIA suya. Eso está bien —tocar la
dieta de un cliente no puede cambiarle las kcal a la biblioteca— pero se hacía
en un solo sentido: corregir el catálogo no llegaba a ninguna dieta. El coach
arreglaba un dato mal, lo veía cambiado en la biblioteca, y sus dietas seguían
con el número viejo sin más salida que rehacerlas.

La regla nueva: la corrección baja a las copias que SIGUEN IGUAL que estaba el
catálogo antes del cambio, campo a campo. Una copia que ya diga otra cosa es
que alguien la puso así y no se pisa.

Lo que hay que dejar sujeto:

  · Que corregir kcal, unidad o fibra se vea en la dieta.
  · Que llegue a la copia de la copia: asignar una dieta a un cliente copia lo
    que ya era una copia, y ahí es donde más importa.
  · Que solo cambie lo corregido, no el alimento entero.
  · Y que no toque a los demás alimentos ni a las copias que alguien cambió.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment

from tests.test_macros_porcion import _monta


def _alimento(client, h, nombre, **campos):
    body = {"name": nombre, "calories": 100, "proteins": 10, "carbohydrates": 5,
            "fats": 2, "quantity": 100, "quantity_unit": "g"}
    body.update(campos)
    r = client.post("/api/aliments", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _dieta_con(client, h, suf, aliment_id, cantidad=100):
    r = client.post("/api/diets", headers=h, json={
        "title": f"Dieta {suf}",
        "foods": [{"name": "Desayuno", "time": "08:00", "detail": [
            {"aliment_id": aliment_id, "quantity_calc": cantidad, "order": 0}]}]})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _corregir(client, h, aliment_id, **campos):
    r = client.put(f"/api/aliments/{aliment_id}/update", headers=h, json=campos)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _en_la_dieta(client, h, diet_id):
    """El alimento tal y como lo ve el editor de dietas."""
    d = client.get(f"/api/diets/{diet_id}/edit", headers=h).json()["data"]
    return d["foods"][0]["detail"][0]["aliment"]


# ── La corrección llega ────────────────────────────────────────────────────

def test_CORREGIR_LAS_KCAL_SE_VE_EN_LA_DIETA(client, seed, admin_headers):
    """El caso reportado: se corrige en la lista de alimentos y en las dietas
    no cambia nada."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pan = _alimento(client, h, f"Pan {suf}", calories=250)
    dieta = _dieta_con(client, h, suf, pan)
    assert _en_la_dieta(client, h, dieta)["calories"] == 250

    _corregir(client, h, pan, calories=265)

    assert _en_la_dieta(client, h, dieta)["calories"] == 265


def test_y_las_kcal_de_la_dieta_se_recalculan(client, seed, admin_headers):
    """No basta con que cambie el alimento: el total de la dieta es lo que
    mira el coach."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pan = _alimento(client, h, f"Pan {suf}", calories=250)
    dieta = _dieta_con(client, h, suf, pan, cantidad=200)

    _corregir(client, h, pan, calories=265)

    d = client.get(f"/api/diets/{dieta}/edit", headers=h).json()["data"]
    assert d["calories"] == 530, d["calories"]      # 265/100 * 200


def test_la_unidad_corregida_tambien(client, seed, admin_headers):
    """Un huevo medido por unidades: si la copia se queda en gramos, la dieta
    sigue diciendo "2 g de huevo" con las kcal de dos gramos."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    huevo = _alimento(client, h, f"Huevo {suf}", calories=74, quantity=100, quantity_unit="g")
    dieta = _dieta_con(client, h, suf, huevo, cantidad=2)

    _corregir(client, h, huevo, quantity=1, quantity_unit="ud")

    al = _en_la_dieta(client, h, dieta)
    assert (al["quantity"], al["quantity_unit"]) == (1, "ud"), al
    d = client.get(f"/api/diets/{dieta}/edit", headers=h).json()["data"]
    assert d["calories"] == 148, d["calories"]      # 74 por unidad, dos huevos


def test_la_fibra_corregida_tambien(client, seed, admin_headers):
    """La fibra vive en la ficha de micros, que es otra tabla."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    fresa = _alimento(client, h, f"Fresa {suf}", description={"fiber": 0})
    dieta = _dieta_con(client, h, suf, fresa)

    _corregir(client, h, fresa, description={"fiber": 2.2})

    assert _en_la_dieta(client, h, dieta)["fiber"] == 2.2


def test_una_copia_sin_ficha_recibe_la_del_catalogo(client, seed, admin_headers):
    """El alimento no tenía micros cuando se copió y ahora sí."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    avena = _alimento(client, h, f"Avena {suf}")
    dieta = _dieta_con(client, h, suf, avena)
    assert _en_la_dieta(client, h, dieta)["fiber"] is None

    _corregir(client, h, avena, description={"fiber": 9.0})

    assert _en_la_dieta(client, h, dieta)["fiber"] == 9.0


def test_LLEGA_A_LA_DIETA_DEL_CLIENTE_QUE_ES_COPIA_DE_UNA_COPIA(client, seed, admin_headers):
    """Asignar una dieta copia lo que ya era una copia. Si la corrección se
    queda en el primer escalón, el que come mal es el cliente."""
    suf = uuid.uuid4().hex[:8]
    h, det_cli, h_cli = _monta(client, admin_headers, suf)
    pan = _alimento(client, h, f"Pan {suf}", calories=250)
    dieta = _dieta_con(client, h, suf, pan)
    r = client.post(f"/api/diets/{dieta}/assign", headers=h, json={"client_id": det_cli})
    assert r.status_code == 200, r.text
    del_cliente = r.json()["data"]["id"]
    assert _en_la_dieta(client, h, del_cliente)["calories"] == 250

    _corregir(client, h, pan, calories=265)

    assert _en_la_dieta(client, h, dieta)["calories"] == 265, "la del coach"
    assert _en_la_dieta(client, h, del_cliente)["calories"] == 265, "la del cliente"


# ── Lo que NO se toca ──────────────────────────────────────────────────────

def test_solo_cambia_lo_corregido(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pan = _alimento(client, h, f"Pan {suf}", calories=250, proteins=8)
    dieta = _dieta_con(client, h, suf, pan)

    _corregir(client, h, pan, calories=265)

    al = _en_la_dieta(client, h, dieta)
    assert al["proteins"] == 8, al
    assert al["name"] == f"Pan {suf}", al


def test_UNA_COPIA_QUE_ALGUIEN_CAMBIO_NO_SE_PISA(client, seed, admin_headers):
    """Y campo a campo: se corrigen las kcal sin tocar el nombre que alguien
    puso a mano en esa dieta."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pan = _alimento(client, h, f"Pan {suf}", calories=250)
    dieta = _dieta_con(client, h, suf, pan)

    copia_id = client.get(f"/api/diets/{dieta}/edit", headers=h) \
        .json()["data"]["foods"][0]["detail"][0]["aliment_id"]
    db = SessionLocal()
    try:
        copia = db.query(Aliment).filter(Aliment.id == copia_id).first()
        copia.name = "Pan del cliente"
        db.commit()
    finally:
        db.close()

    _corregir(client, h, pan, calories=265, name=f"Pan integral {suf}")

    al = _en_la_dieta(client, h, dieta)
    assert al["name"] == "Pan del cliente", "ha pisado un nombre puesto a mano"
    assert al["calories"] == 265, "y no ha corregido las kcal, que sí tocaba"


def test_no_toca_las_copias_de_otro_alimento(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pan = _alimento(client, h, f"Pan {suf}", calories=250)
    arroz = _alimento(client, h, f"Arroz {suf}", calories=130)
    dieta_arroz = _dieta_con(client, h, suf, arroz)

    _corregir(client, h, pan, calories=265)

    assert _en_la_dieta(client, h, dieta_arroz)["calories"] == 130


def test_guardar_sin_cambiar_nada_no_toca_las_copias(client, seed, admin_headers):
    """Abrir el alimento y darle a guardar no puede reescribir media base."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pan = _alimento(client, h, f"Pan {suf}", calories=250)
    dieta = _dieta_con(client, h, suf, pan)

    copia_id = client.get(f"/api/diets/{dieta}/edit", headers=h) \
        .json()["data"]["foods"][0]["detail"][0]["aliment_id"]
    db = SessionLocal()
    try:
        db.query(Aliment).filter(Aliment.id == copia_id).first().name = "Pan del cliente"
        db.commit()
    finally:
        db.close()

    _corregir(client, h, pan, calories=250)

    assert _en_la_dieta(client, h, dieta)["name"] == "Pan del cliente"
