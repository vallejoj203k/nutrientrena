"""El camino del cliente: cómo llega el check-in a la bandeja del coach.

Hay dos puertas, y las dos tienen que dejar las mismas cosas registradas:

  · `POST /calendar-tasks/{id}/checkin` — desde la tarea concreta del
    calendario ("Mi Agenda").
  · `POST /client/checkin` — desde la pantalla de progreso, que ya existía y
    solo aceptaba números de báscula. Sin las cuatro puntuaciones, la bandeja
    del coach enseñaba los cuatro huecos siempre vacíos por este camino.

Y una que hay que cerrar: marcar la tarea de check-in como "hecha" con la
casilla genérica. Le quitaba al coach la señal de que faltaba un check-in sin
que hubiera llegado ninguno.
"""
import uuid
from datetime import date

from app.database import SessionLocal
from app.models.user import UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario


def _monta(client, admin_headers, suf):
    _uid, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.env.{suf}@nutrientrena-qa.com")
    _u2, det_cli, h_cli = _crear_usuario(
        client, admin_headers, f"cli.env.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        db.commit()
    finally:
        db.close()
    return h_coach, det_cli, h_cli


def _tarea(client, h_coach, det_cli, cuando=None):
    r = client.post("/api/calendar-tasks", headers=h_coach, json={
        "client_user_detail_id": det_cli,
        "task_date": (cuando or date.today()).isoformat(),
        "task_type": "checkin",
        "title": "Check-in semanal",
    })
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _bandeja(client, h_coach):
    r = client.get("/api/checkins/bandeja", headers=h_coach)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_desde_progreso_tambien_se_mandan_las_sensaciones(client, seed, admin_headers):
    """Es la pantalla que ya usaban los clientes; si solo se hubiera arreglado
    la otra puerta, seguirían llegando check-ins sin puntuaciones."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det_cli, h_cli = _monta(client, admin_headers, suf)

    r = client.post("/api/client/checkin", headers=h_cli, json={
        "weight": 68.2, "energy": 9, "effort": 7, "hunger": 3, "sleep": 8,
    })
    assert r.status_code == 200, r.text

    fila = _bandeja(client, h_coach)["recibidos"][0]
    assert [fila["energy"], fila["effort"], fila["hunger"], fila["sleep"]] == [9, 7, 3, 8], fila


def test_mandarlo_desde_progreso_cumple_la_tarea_del_calendario(client, seed, admin_headers):
    """Las dos puertas dan al mismo sitio: si envía por progreso, deja de
    estar en falta."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    _tarea(client, h_coach, det_cli)
    assert len(_bandeja(client, h_coach)["esperando"]) == 1

    client.post("/api/client/checkin", headers=h_cli, json={"weight": 68.2})
    assert _bandeja(client, h_coach)["esperando"] == []


def test_el_cliente_no_puede_dar_por_hecho_un_check_in_sin_enviarlo(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    tarea = _tarea(client, h_coach, det_cli)

    r = client.patch(f"/api/calendar-tasks/{tarea}/done", headers=h_cli, json={"done": True})
    assert r.status_code == 400, r.text
    # Y sigue reclamándose, que es el punto.
    assert len(_bandeja(client, h_coach)["esperando"]) == 1


def test_el_coach_si_puede_perdonar_la_semana(client, seed, admin_headers):
    """Cerrar la puerta al cliente no puede cerrársela al coach: a veces la
    semana se da por buena sin check-in (una lesión, un viaje)."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, _h_cli = _monta(client, admin_headers, suf)
    tarea = _tarea(client, h_coach, det_cli)

    r = client.patch(f"/api/calendar-tasks/{tarea}/done", headers=h_coach, json={"done": True})
    assert r.status_code == 200, r.text
    assert _bandeja(client, h_coach)["esperando"] == []


def test_una_tarea_que_no_es_check_in_se_marca_como_siempre(client, seed, admin_headers):
    """El cierre es para las de check-in; el resto las cumple el cliente
    marcándolas, y eso no puede haberse roto."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    r = client.post("/api/calendar-tasks", headers=h_coach, json={
        "client_user_detail_id": det_cli,
        "task_date": date.today().isoformat(),
        "task_type": "cardio",
        "title": "40 min de bici",
    })
    tarea = r.json()["data"]["id"]

    r2 = client.patch(f"/api/calendar-tasks/{tarea}/done", headers=h_cli, json={"done": True})
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["done"] is True
