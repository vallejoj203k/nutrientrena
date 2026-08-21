"""Dos cosas del panel del cliente que no funcionaban.

1. La tira de días era adorno. Se podía cambiar de semana, pero no de día: el
   entrenamiento y el menú de abajo eran SIEMPRE los de hoy. Mirar el miércoles
   y ver la comida del lunes es peor que no poder mirarlo.

2. Un formulario programado por el coach no se podía abrir. La tarea guarda el
   id de la PLANTILLA, pero un cliente no rellena una plantilla: rellena una
   asignación suya, que es la que recoge sus respuestas. Ese salto no lo daba
   nadie, así que en su pantalla solo quedaba "marcar hecho" — o sea, decir que
   lo había rellenado sin haberlo rellenado.
"""
import json
import uuid
from datetime import date, timedelta

from app.database import SessionLocal
from app.models.form import FormAssignment, FormTemplate
from app.models.user import UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario


def _monta(client, admin_headers, suf):
    _u, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.pc.{suf}@nutrientrena-qa.com")
    _uid, det_cli, h_cli = _crear_usuario(
        client, admin_headers, f"cli.pc.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        db.commit()
    finally:
        db.close()
    return det_coach, h_coach, det_cli, h_cli


def _inicio(client, h_cli, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    r = client.get(f"/api/client/home{'?' + q if q else ''}", headers=h_cli)
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ── La tira de días ─────────────────────────────────────────────────────────

def test_por_defecto_se_mira_hoy(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, _hc, _det, h_cli = _monta(client, admin_headers, suf)
    d = _inicio(client, h_cli)["dia_visto"]
    assert d["fecha"] == date.today().isoformat() and d["es_hoy"] is True, d


def test_se_puede_mirar_otro_dia(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, _hc, _det, h_cli = _monta(client, admin_headers, suf)
    otro = date.today() - timedelta(days=2)

    d = _inicio(client, h_cli, dia=otro.isoformat())["dia_visto"]
    assert d["fecha"] == otro.isoformat(), d
    assert d["es_hoy"] is False, d
    assert d["day"] == otro.day, d


def test_la_tira_marca_cual_se_esta_mirando(client, seed, admin_headers):
    """Sin esto el cliente pulsa un día y nada le dice que cambió."""
    suf = uuid.uuid4().hex[:8]
    _dc, _hc, _det, h_cli = _monta(client, admin_headers, suf)
    otro = date.today() - timedelta(days=2)

    dias = _inicio(client, h_cli, dia=otro.isoformat())["week"]["days"]
    marcados = [x for x in dias if x.get("is_selected")]
    assert len(marcados) == 1 and marcados[0]["date"] == otro.isoformat(), marcados


def test_una_fecha_ilegible_no_rompe_la_pantalla(client, seed, admin_headers):
    """Llega por la URL: cualquiera puede escribir cualquier cosa."""
    suf = uuid.uuid4().hex[:8]
    _dc, _hc, _det, h_cli = _monta(client, admin_headers, suf)
    d = _inicio(client, h_cli, dia="martes-que-viene")["dia_visto"]
    assert d["fecha"] == date.today().isoformat(), d


# ── El formulario ───────────────────────────────────────────────────────────

def _plantilla(nombre, creador=1):
    db = SessionLocal()
    try:
        t = FormTemplate(title=nombre, category="checkin", created_by=creador)
        db.add(t)
        db.commit()
        return t.id
    finally:
        db.close()


def _tarea_formulario(client, h_coach, det_cli, plantilla_id):
    r = client.post("/api/calendar-tasks", headers=h_coach, json={
        "client_user_detail_id": det_cli,
        "task_date": date.today().isoformat(),
        "task_type": "formulario",
        "title": "Formulario Check in",
        "requirements": {"form_template_id": plantilla_id, "form_name": "Check in"},
    })
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _peticiones(client, h_cli):
    r = client.get("/api/client/requests", headers=h_cli)
    assert r.status_code == 200, r.text
    return r.json()["data"]["items"]


def test_el_cliente_recibe_el_enlace_para_rellenarlo(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    plantilla = _plantilla(f"Check in {suf}")
    _tarea_formulario(client, h_coach, det_cli, plantilla)

    fila = next(x for x in _peticiones(client, h_cli) if x["task_type"] == "formulario")
    assert fila["action"] == "formulario", fila
    assert fila.get("form_assignment_id"), fila


def test_la_asignacion_es_suya_y_de_esa_plantilla(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    plantilla = _plantilla(f"Check in {suf}")
    _tarea_formulario(client, h_coach, det_cli, plantilla)

    aid = next(x for x in _peticiones(client, h_cli)
               if x["task_type"] == "formulario")["form_assignment_id"]
    db = SessionLocal()
    try:
        a = db.query(FormAssignment).filter(FormAssignment.id == aid).first()
        assert a.client_user_detail_id == det_cli, a.client_user_detail_id
        assert a.form_template_id == plantilla, a.form_template_id
    finally:
        db.close()


def test_mirarlo_dos_veces_no_crea_dos_formularios(client, seed, admin_headers):
    """Si se creara uno por visita, el cliente acabaría con veinte iguales."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    plantilla = _plantilla(f"Check in {suf}")
    _tarea_formulario(client, h_coach, det_cli, plantilla)

    ids = set()
    for _ in range(3):
        ids.add(next(x for x in _peticiones(client, h_cli)
                     if x["task_type"] == "formulario")["form_assignment_id"])
    assert len(ids) == 1, ids

    db = SessionLocal()
    try:
        n = db.query(FormAssignment).filter(
            FormAssignment.client_user_detail_id == det_cli,
            FormAssignment.form_template_id == plantilla,
        ).count()
        assert n == 1, n
    finally:
        db.close()


def test_el_enlace_abre_de_verdad_ese_formulario(client, seed, admin_headers):
    """La ruta pública es la que usa la página que rellena el cliente: si
    devolviera 404, el botón llevaría a una pantalla rota."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    plantilla = _plantilla(f"Check in {suf}")
    _tarea_formulario(client, h_coach, det_cli, plantilla)

    aid = next(x for x in _peticiones(client, h_cli)
               if x["task_type"] == "formulario")["form_assignment_id"]
    assert client.get(f"/api/public/form/{aid}").status_code == 200


def test_sin_plantilla_detras_no_se_promete_un_enlace(client, seed, admin_headers):
    """Una tarea de formulario mal creada tiene que quedarse como tarea normal,
    no llevar a una página vacía."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    r = client.post("/api/calendar-tasks", headers=h_coach, json={
        "client_user_detail_id": det_cli,
        "task_date": date.today().isoformat(),
        "task_type": "formulario",
        "title": "Formulario suelto",
    })
    assert r.status_code == 200, r.text

    fila = next(x for x in _peticiones(client, h_cli) if x["task_type"] == "formulario")
    assert fila["action"] is None, fila
    assert not fila.get("form_assignment_id"), fila


def test_una_tarea_creada_antes_del_arreglo_tambien_se_repara(client, seed, admin_headers):
    """Es el caso que el coach tiene hoy en pantalla: la tarea ya existía con
    solo el id de plantilla."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    plantilla = _plantilla(f"Check in {suf}")
    tarea = _tarea_formulario(client, h_coach, det_cli, plantilla)

    # Se deja como estaba antes: sin form_assignment_id.
    from app.models.calendar_task import CalendarTask
    db = SessionLocal()
    try:
        t = db.query(CalendarTask).filter(CalendarTask.id == tarea).first()
        t.requirements = json.dumps({"form_template_id": plantilla, "form_name": "Check in"})
        db.commit()
    finally:
        db.close()

    fila = next(x for x in _peticiones(client, h_cli) if x["task_type"] == "formulario")
    assert fila.get("form_assignment_id"), fila
