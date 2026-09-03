"""Prot / Carb / Grasa en la lista de dietas, cuando el coach no las escribió.

En la biblioteca, una dieta montada en modo "kcal" —el coach escribe las
kcal objetivo y no toca los macros— salía con 1439 kcal y tres guiones al
lado, con las comidas enteras debajo. La lista rellenaba los macros a partir
de los alimentos SOLO cuando tampoco había kcal: bastaba con tener kcal para
que no rellenara nada.

Lo que hay que dejar sujeto:

  · Que cada cifra se rellene por su cuenta: kcal escritas y macros sumados.
  · Que lo que el coach escribió no se pise con la suma.
  · Y que la suma respete la porción del alimento, como en todas partes.
"""
import uuid

from tests.test_macros_porcion import _alimento, _monta


def _crear(client, h_coach, suf, foods, **objetivo):
    r = client.post("/api/diets", headers=h_coach, json={
        "title": f"Low Carb {suf}", "foods": foods, **objetivo})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _en_lista(client, h_coach, did):
    dietas = client.get("/api/diets/findAll", headers=h_coach).json()["data"]
    mias = [d for d in dietas if d["id"] == did]
    assert mias, "la dieta no sale en la lista"
    return mias[0]


# El pollo de pruebas lleva 10 g de proteína, 1 de carbo y 5 de grasa por
# porción de 100 g. 150 g -> 15 / 1.5 / 7.5.
def _pollo(suf):
    return _alimento(f"Pollo {suf}", 165.0, 100.0, "g")


def test_CON_KCAL_ESCRITAS_LOS_MACROS_SE_SUMAN_IGUAL(client, seed, admin_headers):
    """El caso de la captura: kcal 1439, Prot —, Carb —, Grasa —."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear(client, h_coach, suf, calories=1500, foods=[
        {"name": "Comida", "time": "14:00", "detail": [
            {"aliment_id": _pollo(suf), "quantity_calc": 150, "order": 0}]}])

    d = _en_lista(client, h_coach, did)
    assert d["calories"] == 1500, "las kcal escritas son las que mandan"
    det = d["detail"] or {}
    assert det.get("proteins") == 15, det
    assert det.get("carbs") == 1.5, det
    assert det.get("fats") == 7.5, det


def test_lo_que_escribio_el_coach_no_se_pisa(client, seed, admin_headers):
    """Modo "macros": el objetivo son 120 g de proteína aunque la comida
    montada hoy sume 15."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear(client, h_coach, suf, calories=1500, proteins=120, carbs=100, fats=50,
                 foods=[{"name": "Comida", "time": "14:00", "detail": [
                     {"aliment_id": _pollo(suf), "quantity_calc": 150, "order": 0}]}])

    det = _en_lista(client, h_coach, did)["detail"]
    assert (det["proteins"], det["carbs"], det["fats"]) == (120, 100, 50), det


def test_el_detalle_de_la_dieta_dice_lo_mismo_que_la_lista(client, seed, admin_headers):
    """La lista y el previo leen el mismo dato; si divergieran, el coach
    vería una cifra en la fila y otra al abrirla."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear(client, h_coach, suf, calories=1500, foods=[
        {"name": "Comida", "time": "14:00", "detail": [
            {"aliment_id": _pollo(suf), "quantity_calc": 150, "order": 0}]}])

    lista = _en_lista(client, h_coach, did)["detail"]
    previo = client.get(f"/api/diets/{did}/edit", headers=h_coach).json()["data"]["detail"]
    assert (previo["proteins"], previo["carbs"], previo["fats"]) == \
        (lista["proteins"], lista["carbs"], lista["fats"])


def test_la_suma_respeta_la_porcion_del_alimento(client, seed, admin_headers):
    """Dos huevos por unidad: 20 g de proteína, no 0,2."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    huevo = _alimento(f"Huevo {suf}", 74.0, 1.0, "ud")
    did = _crear(client, h_coach, suf, calories=1500, foods=[
        {"name": "Desayuno", "time": "08:00", "detail": [
            {"aliment_id": huevo, "quantity_calc": 2, "order": 0}]}])

    det = _en_lista(client, h_coach, did)["detail"]
    assert det["proteins"] == 20, det
    assert det["fats"] == 10, det


def test_sin_alimentos_no_se_inventa_nada(client, seed, admin_headers):
    """Una dieta con kcal objetivo y sin comidas todavía: los macros siguen
    vacíos, que es la verdad, no un 0 que parezca un dato."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear(client, h_coach, suf, calories=1500, foods=[])

    d = _en_lista(client, h_coach, did)
    assert d["calories"] == 1500
    det = d.get("detail") or {}
    assert not det.get("proteins") and not det.get("carbs") and not det.get("fats"), det
