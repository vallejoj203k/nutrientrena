"""La bandeja de check-ins del coach.

La pantalla responde a tres preguntas y la bandeja devuelve una lista para cada
una: qué me ha llegado y no he mirado, a quién le tocaba y no ha enviado, y qué
he despachado hoy.

Dos cosas que no existían y hacían falta:

  · Las cuatro puntuaciones (energía, esfuerzo, hambre, descanso). La ficha del
    cliente ya las pintaba desde hace tiempo y siempre salían "—" porque el
    campo no se había creado nunca.
  · La marca de revisado. Antes solo se sabía si el coach había escrito notas,
    y "lo he leído y está todo bien" no deja notas: ese check-in se quedaba
    pendiente para siempre.

Quién manda el check-in es el CLIENTE, cumpliendo la tarea que su coach le puso
en el calendario. Y a quién le "toca" lo dice esa misma tarea: no hay una
cadencia inventada por el sistema.
"""
import uuid
from datetime import date, timedelta

from app.database import SessionLocal
from app.models.calendar_task import CalendarTask
from app.models.user import UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario


def _cliente_de(client, admin_headers, coach_detail_id, email):
    _uid, det, h = _crear_usuario(client, admin_headers, email, role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det, parent_user_detail_id=coach_detail_id))
        db.commit()
    finally:
        db.close()
    return det, h


def _monta(client, admin_headers, suf):
    _uid, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.ci.{suf}@nutrientrena-qa.com")
    det_cli, h_cli = _cliente_de(client, admin_headers, det_coach,
                                 f"cli.ci.{suf}@nutrientrena-qa.com")
    return det_coach, h_coach, det_cli, h_cli


def _tarea_checkin(client, h_coach, det_cli, cuando: date):
    r = client.post("/api/calendar-tasks", headers=h_coach, json={
        "client_user_detail_id": det_cli,
        "task_date": cuando.isoformat(),
        "task_type": "checkin",
        "title": "Check-in semanal",
    })
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _bandeja(client, h_coach):
    r = client.get("/api/checkins/bandeja", headers=h_coach)
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ── Lo envía el cliente ────────────────────────────────────────────────────

def test_el_cliente_envia_su_check_in_desde_su_tarea(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    tarea = _tarea_checkin(client, h_coach, det_cli, date.today())

    r = client.post(f"/api/calendar-tasks/{tarea}/checkin", headers=h_cli, json={
        "weight": 71.6, "energy": 8, "effort": 8, "hunger": 4, "sleep": 7,
        "notes": "Semana dura pero bien",
    })
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["task"]["done"] is True, d["task"]
    assert d["task"]["checkin_id"], d["task"]


def test_las_cuatro_puntuaciones_se_guardan(client, seed, admin_headers):
    """Existen justo para esto: la ficha del cliente las pedía y salían "—"."""
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    tarea = _tarea_checkin(client, h_coach, det_cli, date.today())
    client.post(f"/api/calendar-tasks/{tarea}/checkin", headers=h_cli,
                json={"weight": 71.6, "energy": 8, "effort": 6, "hunger": 4, "sleep": 7})

    fila = _bandeja(client, h_coach)["recibidos"][0]
    assert [fila["energy"], fila["effort"], fila["hunger"], fila["sleep"]] == [8, 6, 4, 7], fila
    assert fila["weight"] == 71.6


def test_un_cliente_no_envia_el_check_in_de_otro(client, seed, admin_headers):
    """Con el id de la tarea a mano estaría escribiendo el peso y las fotos de
    otra persona."""
    suf = uuid.uuid4().hex[:8]
    det_coach, h_coach, _det_cli, _h_cli = _monta(client, admin_headers, suf)
    otro_det, _h_otro = _cliente_de(client, admin_headers, det_coach,
                                    f"otro.ci.{suf}@nutrientrena-qa.com")
    tarea_ajena = _tarea_checkin(client, h_coach, otro_det, date.today())

    _d2, h_intruso = _cliente_de(client, admin_headers, det_coach,
                                 f"intruso.ci.{suf}@nutrientrena-qa.com")
    r = client.post(f"/api/calendar-tasks/{tarea_ajena}/checkin", headers=h_intruso,
                    json={"weight": 99})
    assert r.status_code == 403, r.text


# ── Lo recibido ────────────────────────────────────────────────────────────

def test_lo_enviado_aparece_por_revisar(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    tarea = _tarea_checkin(client, h_coach, det_cli, date.today())
    client.post(f"/api/calendar-tasks/{tarea}/checkin", headers=h_cli,
                json={"weight": 70, "notes": "hola", "photo_url": "u1", "photo2": "u2"})

    b = _bandeja(client, h_coach)
    assert len(b["recibidos"]) == 1, b
    fila = b["recibidos"][0]
    assert fila["fotos"] == 2 and fila["tiene_comentario"] is True, fila
    assert fila["iniciales"], fila
    # Y ya no está esperándose, porque la tarea quedó cumplida.
    assert b["esperando"] == [], b


def test_solo_veo_los_check_ins_de_MIS_clientes(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dcA, h_coachA, det_cliA, h_cliA = _monta(client, admin_headers, suf + "a")
    _dcB, h_coachB, det_cliB, h_cliB = _monta(client, admin_headers, suf + "b")
    tA = _tarea_checkin(client, h_coachA, det_cliA, date.today())
    tB = _tarea_checkin(client, h_coachB, det_cliB, date.today())
    client.post(f"/api/calendar-tasks/{tA}/checkin", headers=h_cliA, json={"weight": 70})
    client.post(f"/api/calendar-tasks/{tB}/checkin", headers=h_cliB, json={"weight": 80})

    pesos = [f["weight"] for f in _bandeja(client, h_coachA)["recibidos"]]
    assert pesos == [70], pesos


# ── Lo que falta ───────────────────────────────────────────────────────────

def test_quien_no_ha_enviado_aparece_esperando(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h_cli = _monta(client, admin_headers, suf)
    _tarea_checkin(client, h_coach, det_cli, date.today() - timedelta(days=3))

    b = _bandeja(client, h_coach)
    assert len(b["esperando"]) == 1, b
    assert b["esperando"][0]["dias_de_retraso"] == 3, b["esperando"][0]


def test_una_tarea_de_mañana_no_se_reclama_todavia(client, seed, admin_headers):
    """Le toca el viernes: el martes no está en falta."""
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h_cli = _monta(client, admin_headers, suf)
    _tarea_checkin(client, h_coach, det_cli, date.today() + timedelta(days=2))
    assert _bandeja(client, h_coach)["esperando"] == []


def test_un_cliente_con_tres_pendientes_sale_una_sola_vez(client, seed, admin_headers):
    """Hay que recordárselo una vez, no tres."""
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h_cli = _monta(client, admin_headers, suf)
    for d in (7, 14, 21):
        _tarea_checkin(client, h_coach, det_cli, date.today() - timedelta(days=d))

    esperando = _bandeja(client, h_coach)["esperando"]
    assert len(esperando) == 1, esperando
    # Se enseña el más antiguo, que es el que de verdad va con retraso.
    assert esperando[0]["dias_de_retraso"] == 21, esperando[0]


# ── Revisar ────────────────────────────────────────────────────────────────

def test_revisar_lo_pasa_a_revisados_hoy(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    tarea = _tarea_checkin(client, h_coach, det_cli, date.today())
    client.post(f"/api/calendar-tasks/{tarea}/checkin", headers=h_cli, json={"weight": 70})
    cid = _bandeja(client, h_coach)["recibidos"][0]["id"]

    r = client.put(f"/api/checkins/{cid}/revisado", headers=h_coach)
    assert r.status_code == 200, r.text

    b = _bandeja(client, h_coach)
    assert b["recibidos"] == [], b
    assert len(b["revisados_hoy"]) == 1, b


def test_se_puede_volver_a_dejarlo_pendiente(client, seed, admin_headers):
    """La pantalla dice "Puedes volver a abrirlos": tiene que ser verdad."""
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    tarea = _tarea_checkin(client, h_coach, det_cli, date.today())
    client.post(f"/api/calendar-tasks/{tarea}/checkin", headers=h_cli, json={"weight": 70})
    cid = _bandeja(client, h_coach)["recibidos"][0]["id"]

    client.put(f"/api/checkins/{cid}/revisado", headers=h_coach)
    client.put(f"/api/checkins/{cid}/revisado?revisado=false", headers=h_coach)

    b = _bandeja(client, h_coach)
    assert len(b["recibidos"]) == 1 and b["revisados_hoy"] == [], b


def test_un_coach_no_revisa_el_check_in_de_un_cliente_ajeno(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dcA, h_coachA, det_cliA, h_cliA = _monta(client, admin_headers, suf + "a")
    _dcB, h_coachB, _det_cliB, _h_cliB = _monta(client, admin_headers, suf + "b")
    tA = _tarea_checkin(client, h_coachA, det_cliA, date.today())
    client.post(f"/api/calendar-tasks/{tA}/checkin", headers=h_cliA, json={"weight": 70})
    cid = _bandeja(client, h_coachA)["recibidos"][0]["id"]

    assert client.put(f"/api/checkins/{cid}/revisado", headers=h_coachB).status_code == 403


def test_un_coach_sin_clientes_recibe_tres_listas_vacias(client, seed, admin_headers):
    """Y no un error: la pantalla tiene que poder pintarse igual."""
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h_coach = _crear_coach(client, admin_headers, f"coach.sinci.{suf}@nutrientrena-qa.com")
    b = _bandeja(client, h_coach)
    assert b == {"recibidos": [], "esperando": [], "revisados_hoy": []}, b
