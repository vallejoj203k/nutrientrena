"""Cuánto aporta una cantidad de un alimento, cuando el alimento no va por 100 g.

La fórmula dividía entre 100 a ciegas en unos cuarenta sitios. Pero no todos los
alimentos vienen por 100 g:

  · Huevo grande: 74 kcal por 1 UNIDAD. Dos huevos daban 1,5 kcal.
  · Cacito de proteína: 117 kcal por 29 g. Un cacito daba 34.
  · Yogur griego: 176 kcal por el envase de 125 g. Un envase daba 220.

Fallaba en las dos direcciones y el total de la dieta descuadraba sin que nadie
supiera por qué. El dato que hacía falta ya estaba guardado —`aliments.quantity`
dice a qué cantidad se refieren esos macros—; nadie lo miraba.

Lo importante de estas comprobaciones: para los alimentos por 100 g el
resultado tiene que ser EXACTAMENTE el de antes. Son la enorme mayoría del
catálogo y un cambio ahí le movería las kcal a dietas que ya están montadas.
"""
import uuid

import pytest

from app.core.macros import escalar, porcion_de
from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.user import UserDetail, UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario


class _Al:
    """Un alimento de mentira, para probar la cuenta sin base de datos."""
    def __init__(self, quantity=None, calories=None):
        self.quantity = quantity
        self.calories = calories


# ── La cuenta ──────────────────────────────────────────────────────────────

def test_LO_QUE_VA_POR_100G_NO_CAMBIA_NADA():
    """Es la enorme mayoría del catálogo. Si esto se moviera, cambiarían las
    kcal de todas las dietas ya montadas."""
    pollo = _Al(quantity=100, calories=165)
    assert escalar(pollo.calories, pollo, 150) == pytest.approx(247.5)
    assert escalar(pollo.calories, pollo, 100) == pytest.approx(165)


def test_UN_ALIMENTO_POR_UNIDAD_YA_CUENTA_BIEN():
    """El caso que se reportó: dos huevos daban 1,5 kcal en vez de 148."""
    huevo = _Al(quantity=1, calories=74)
    assert escalar(huevo.calories, huevo, 2) == pytest.approx(148)
    assert escalar(huevo.calories, huevo, 1) == pytest.approx(74)


def test_y_uno_por_racion_tambien():
    """Fallaba en las dos direcciones: el cacito se quedaba corto y el yogur
    se pasaba."""
    cacito = _Al(quantity=29, calories=117)      # antes daba 34
    assert escalar(cacito.calories, cacito, 29) == pytest.approx(117)
    yogur = _Al(quantity=125, calories=176)      # antes daba 220
    assert escalar(yogur.calories, yogur, 125) == pytest.approx(176)


def test_sin_porcion_se_comporta_como_siempre():
    """Un alimento viejo sin el dato no puede cambiar de comportamiento: se
    sigue dividiendo entre 100, que es lo de toda la vida."""
    assert porcion_de(_Al(quantity=None)) == 100
    assert escalar(200, _Al(quantity=None), 50) == pytest.approx(100)


def test_UNA_PORCION_DE_CERO_NO_REVIENTA_LA_PANTALLA():
    """Un alimento mal metido con cantidad 0 dividiría entre cero y se llevaría
    por delante la dieta entera, no solo esa fila."""
    assert porcion_de(_Al(quantity=0)) == 100
    assert porcion_de(_Al(quantity="")) == 100
    assert porcion_de(_Al(quantity="ocho")) == 100
    assert porcion_de(None) == 100
    assert escalar(100, _Al(quantity=0), 10) == pytest.approx(10)


def test_los_valores_vacios_dan_cero_y_no_error():
    al = _Al(quantity=1, calories=None)
    assert escalar(al.calories, al, 2) == 0
    assert escalar(50, al, None) == 0


# ── Y de punta a punta, que es donde se veía ───────────────────────────────

def _monta(client, admin_headers, suf):
    _u, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.por.{suf}@nutrientrena-qa.com")
    _uid, det_cli, h_cli = _crear_usuario(
        client, admin_headers, f"cli.por.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        db.commit()
    finally:
        db.close()
    return h_coach, det_cli, h_cli


def _alimento(nombre, kcal, porcion, unidad="g"):
    db = SessionLocal()
    try:
        al = Aliment(id=str(uuid.uuid4()), name=nombre, calories=kcal,
                     proteins=10.0, carbohydrates=1.0, fats=5.0,
                     quantity=porcion, quantity_unit=unidad)
        db.add(al)
        db.commit()
        return al.id
    finally:
        db.close()


def _dieta_con(client, h_coach, suf, aliment_id, cantidad):
    r = client.post("/api/diets", headers=h_coach, json={
        "title": f"Dieta {suf}",
        "foods": [{"name": "Desayuno", "time": "08:00",
                   "detail": [{"aliment_id": aliment_id, "quantity_calc": cantidad,
                               "order": 0}]}]})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def test_LA_DIETA_CON_DOS_HUEVOS_SUMA_148_NO_UNO_Y_MEDIO(client, seed, admin_headers):
    """El caso reportado, montando la dieta de verdad y leyendo sus kcal."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    huevo = _alimento(f"Huevo Grande {suf}", 74.0, 1.0, "ud")
    did = _dieta_con(client, h_coach, suf, huevo, 2)

    datos = client.get(f"/api/diets/{did}/edit", headers=h_coach).json()["data"]
    assert datos["calories"] == 148, datos["calories"]


def test_y_la_dieta_por_100g_sigue_dando_lo_mismo_que_siempre(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    pollo = _alimento(f"Pollo {suf}", 165.0, 100.0, "g")
    did = _dieta_con(client, h_coach, suf, pollo, 150)

    datos = client.get(f"/api/diets/{did}/edit", headers=h_coach).json()["data"]
    assert datos["calories"] == 248, datos["calories"]   # 165/100*150 = 247,5


def test_AL_CLIENTE_LE_LLEGAN_LAS_KCAL_BUENAS(client, seed, admin_headers):
    """Es la pantalla que mira el cliente para saber qué come. Si el total le
    llegara mal, seguiría una dieta que no es la que su coach le puso."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    huevo = _alimento(f"Huevo Grande {suf}", 74.0, 1.0, "ud")
    did = _dieta_con(client, h_coach, suf, huevo, 3)
    assert client.post(f"/api/diets/{did}/assign", headers=h_coach,
                       json={"client_id": det_cli}).status_code == 200

    datos = client.get("/api/client/nutrition", headers=h_cli).json()["data"]
    comidas = [m for d in datos["days"] for m in (d.get("meals") or [])]
    assert comidas, datos
    assert comidas[0]["kcal"] == 222, comidas[0]         # 74 * 3


def test_un_alimento_sin_porcion_sigue_saliendo_igual(client, seed, admin_headers):
    """Los que ya estaban en la base sin ese dato no pueden cambiar de número
    de un día para otro."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    viejo = _alimento(f"Alimento viejo {suf}", 200.0, None)
    did = _dieta_con(client, h_coach, suf, viejo, 50)

    datos = client.get(f"/api/diets/{did}/edit", headers=h_coach).json()["data"]
    assert datos["calories"] == 100, datos["calories"]   # 200/100*50
