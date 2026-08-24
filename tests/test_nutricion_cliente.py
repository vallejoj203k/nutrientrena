"""Qué come el cliente cada día, y por qué a veces es siempre lo mismo.

Hay dos formas de darle comida a un cliente, y no hacen lo mismo:

  1. Un MENÚ SEMANAL: una dieta por día. Es la única forma de que el cliente
     coma distinto el lunes y el martes.
  2. Una DIETA suelta asignada al cliente: vale para los siete días.

La segunda repite a propósito, pero la pantalla del cliente enseña una tira de
días arriba que invita a pensar que cada uno trae algo distinto — y cambiar de
día no cambiaba nada, sin ninguna explicación. Ahora la respuesta dice de qué
tipo es el plan (`plan_semanal`) para que la pantalla lo pueda decir.

Y hay un caso que conviene tener escrito: si el coach le asigna VARIAS dietas
sueltas, el cliente solo ve la última. Las demás no aparecen por ningún lado.
No es un fallo de esta pantalla —nadie ha dicho qué día va cada una— pero sí es
material que el coach creó y su cliente no puede alcanzar.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.diet import Diet, DietFood, DietFoodAliment
from app.models.user import UserDetail, UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario


def _monta(client, admin_headers, suf):
    _u, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.nut.{suf}@nutrientrena-qa.com")
    _uid, det_cli, h_cli = _crear_usuario(
        client, admin_headers, f"cli.nut.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        db.commit()
    finally:
        db.close()
    return det_coach, h_coach, det_cli, h_cli


def _dieta_con_comida(client, h_coach, titulo, kcal):
    """Una dieta con una comida distinguible, para poder decir cuál se ve."""
    r = client.post("/api/diets", headers=h_coach, json={"title": titulo})
    assert r.status_code == 200, r.text
    did = r.json()["data"]["id"]

    db = SessionLocal()
    try:
        al = Aliment(id=str(uuid.uuid4()), name=f"Alimento de {titulo}",
                     calories=100.0, quantity_unit="g")
        db.add(al)
        db.flush()
        d = db.query(Diet).filter(Diet.id == did).first()
        d.calories = kcal
        comida = DietFood(diet_id=did, name=f"Comida de {titulo}", time="08:00")
        db.add(comida)
        db.flush()
        db.add(DietFoodAliment(diet_id=did, diet_food_id=comida.id,
                               aliment_id=al.id, quantity=100.0, order=0))
        db.commit()
    finally:
        db.close()
    return did


def _asignar_directa(did, det_cli):
    """Como hace la ficha del cliente: la dieta pasa a ser del cliente."""
    db = SessionLocal()
    try:
        ud = db.query(UserDetail).filter(UserDetail.id == det_cli).first()
        db.query(Diet).filter(Diet.id == did).first().user_id = ud.user_id
        db.commit()
    finally:
        db.close()


def _nutricion(client, h_cli):
    r = client.get("/api/client/nutrition", headers=h_cli)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _comidas_por_dia(datos):
    return [((d.get("meals") or [{}])[0].get("name") if d.get("meals") else None)
            for d in datos["days"]]


# ── Una dieta suelta: la misma todos los días, y se dice ────────────────────

def test_una_dieta_suelta_vale_para_toda_la_semana(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    _asignar_directa(_dieta_con_comida(client, h_coach, f"Plan unico {suf}", 2000), det_cli)

    datos = _nutricion(client, h_cli)
    comidas = _comidas_por_dia(datos)
    assert len(set(comidas)) == 1, comidas          # los siete días, lo mismo
    assert comidas[0] is not None, comidas


def test_y_la_pantalla_puede_decir_que_es_el_mismo_plan(client, seed, admin_headers):
    """Sin esto el cliente cambia de día, no ve ningún cambio y no sabe si es
    que la aplicación falla o que su plan es así."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    _asignar_directa(_dieta_con_comida(client, h_coach, f"Plan unico {suf}", 2000), det_cli)

    assert _nutricion(client, h_cli)["plan_semanal"] is False


def test_varias_dietas_sueltas_y_el_cliente_solo_ve_la_ultima(client, seed, admin_headers):
    """El caso que se reportó: «no aparecen todas».

    No es un fallo de esta pantalla —nadie ha dicho qué día va cada dieta— pero
    queda escrito: se cuenta cuántas hay para que se pueda avisar.
    """
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    for n in range(3):
        _asignar_directa(_dieta_con_comida(client, h_coach, f"Plan {n} {suf}", 1000 * (n + 1)), det_cli)

    datos = _nutricion(client, h_cli)
    assert datos["dietas_asignadas"] == 3, datos["dietas_asignadas"]
    assert len(set(_comidas_por_dia(datos))) == 1, _comidas_por_dia(datos)


# ── Un menú semanal: comida distinta cada día ──────────────────────────────

def test_UN_MENU_SEMANAL_SI_DA_COMIDA_DISTINTA_CADA_DIA(client, seed, admin_headers):
    """Es la única forma de comer distinto el lunes y el martes, y funciona."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    d1 = _dieta_con_comida(client, h_coach, f"Lunes {suf}", 1000)
    d2 = _dieta_con_comida(client, h_coach, f"Martes {suf}", 2000)
    d3 = _dieta_con_comida(client, h_coach, f"Miercoles {suf}", 3000)

    menu = client.post("/api/weekly-menus", headers=h_coach, json={
        "name": f"Semana {suf}",
        "days": [
            {"day_index": 0, "name": "Lunes", "diet_id": d1},
            {"day_index": 1, "name": "Martes", "diet_id": d2},
            {"day_index": 2, "name": "Miércoles", "diet_id": d3},
            {"day_index": 3, "name": "Jueves", "diet_id": d1},
            {"day_index": 4, "name": "Viernes", "diet_id": d2},
            {"day_index": 5, "name": "Sábado", "diet_id": None},
            {"day_index": 6, "name": "Domingo", "diet_id": None},
        ]})
    assert menu.status_code == 200, menu.text
    asig = client.post(f"/api/weekly-menus/{menu.json()['data']['id']}/assign",
                       headers=h_coach, json={"client_id": det_cli})
    assert asig.status_code == 200, asig.text

    datos = _nutricion(client, h_cli)
    assert datos["plan_semanal"] is True, datos
    comidas = _comidas_por_dia(datos)
    # Lunes, martes y miércoles distintos entre sí.
    assert len({comidas[0], comidas[1], comidas[2]}) == 3, comidas
    # El jueves repite el del lunes, porque así lo puso el coach.
    assert comidas[3] == comidas[0], comidas
    # Y los días sin dieta se quedan vacíos, no heredan el anterior.
    assert comidas[5] is None and comidas[6] is None, comidas


def test_los_dias_sin_dieta_se_marcan_como_tales(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    d1 = _dieta_con_comida(client, h_coach, f"Solo lunes {suf}", 1500)
    menu = client.post("/api/weekly-menus", headers=h_coach, json={
        "name": f"Semana {suf}",
        "days": [{"day_index": i, "name": f"Día {i}", "diet_id": d1 if i == 0 else None}
                 for i in range(7)]})
    client.post(f"/api/weekly-menus/{menu.json()['data']['id']}/assign",
                headers=h_coach, json={"client_id": det_cli})

    dias = _nutricion(client, h_cli)["days"]
    assert dias[0]["has_diet"] is True, dias[0]
    assert all(d["has_diet"] is False for d in dias[1:]), [d["has_diet"] for d in dias]


def test_sin_nada_asignado_no_revienta(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, _hc, _det, h_cli = _monta(client, admin_headers, suf)
    datos = _nutricion(client, h_cli)
    assert datos["days"] == [] and datos["menu"] is None, datos
