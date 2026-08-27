"""Los dos modos de programar la nutrición de un cliente.

Hay dos formas de darle de comer a alguien y hasta ahora convivían sin decirlo:
un plan semanal que se repite, y el calendario día a día. El coach podía
programar el calendario y el cliente seguía viendo el plan semanal — cada uno
mirando una cosa distinta, y nadie enterándose.

Ahora manda uno solo. Lo que hay que dejar sujeto:

  · La pausa es DE VERDAD. Con el calendario activo, el plan semanal deja de
    llegarle al cliente. Si no, el aviso de "queda en pausa" es mentira.
  · Y la pausa NO borra. Volver al plan semanal tiene que devolver exactamente
    lo que había: es lo que promete la ventana de confirmación.
  · Un modo mal escrito se rechaza. Guardar "calendarío" dejaría al cliente sin
    plan de ninguno de los dos tipos, y eso no se nota hasta que pregunta.
"""
import json
import uuid
from datetime import date, timedelta

from app.database import SessionLocal
from app.models.calendar_task import CalendarTask
from app.models.user import UserDetail

from tests.test_lista_compra import _dieta_con
from tests.test_nutricion_cliente import _asignar_directa, _monta, _nutricion


def _modo(client, headers, det_cli, modo):
    return client.put(f"/api/users/client/{det_cli}/nutrition-mode",
                      headers=headers, json={"nutrition_mode": modo})


def _tarea_de_dieta(det_cli, coach_user_id, dia, did, titulo="Dieta del día"):
    """Como la crea el calendario: la dieta va dentro de `requirements`."""
    db = SessionLocal()
    try:
        db.add(CalendarTask(
            client_user_detail_id=det_cli, coach_user_id=coach_user_id,
            task_date=dia, task_type="nutricion", title=titulo,
            requirements=json.dumps({"diet_id": did})))
        db.commit()
    finally:
        db.close()


def _coach_user_id(det_coach):
    db = SessionLocal()
    try:
        return db.query(UserDetail).filter(UserDetail.id == det_coach).first().user_id
    finally:
        db.close()


def _lunes():
    hoy = date.today()
    return hoy - timedelta(days=hoy.weekday())


# ── Guardar el modo ────────────────────────────────────────────────────────

def test_el_modo_se_guarda(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _h = _monta(client, admin_headers, suf)

    r = _modo(client, h_coach, det_cli, "calendario")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["nutrition_mode"] == "calendario"

    db = SessionLocal()
    try:
        assert db.query(UserDetail).filter(
            UserDetail.id == det_cli).first().nutrition_mode == "calendario"
    finally:
        db.close()


def test_UN_MODO_INVENTADO_SE_RECHAZA(client, seed, admin_headers):
    """Guardar cualquier cosa dejaría al cliente sin plan de ninguno de los dos
    tipos, y eso no se nota hasta que pregunta qué tiene que comer."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _h = _monta(client, admin_headers, suf)
    r = _modo(client, h_coach, det_cli, "calendarío")
    assert r.status_code == 400, r.text

    db = SessionLocal()
    try:
        assert db.query(UserDetail).filter(
            UserDetail.id == det_cli).first().nutrition_mode != "calendarío"
    finally:
        db.close()


def test_un_coach_no_cambia_el_modo_de_un_cliente_ajeno(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, _h_coach, det_cli, _h = _monta(client, admin_headers, suf)
    from tests.test_org_scope import _crear_coach, _crear_organizacion
    _u, det_otro, h_otro = _crear_coach(
        client, admin_headers, f"coach.otro.{suf}@nutrientrena-qa.com")
    _crear_organizacion(det_otro, f"Otro centro {suf}")

    r = _modo(client, h_otro, det_cli, "calendario")
    assert r.status_code in (403, 404), r.status_code


# ── Que la pausa sea de verdad ─────────────────────────────────────────────

def test_CON_EL_CALENDARIO_ACTIVO_EL_PLAN_SEMANAL_NO_LLEGA(client, seed, admin_headers):
    """Es lo que promete la ventana: "tu plan semanal quedará en pausa". Si el
    cliente siguiera viéndolo, el coach programaría una cosa y su cliente
    comería otra."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h_coach, f"Semanal {suf}", [
        (f"Pollo {suf}", f"Aves {suf}", 120.0, "g")])
    _asignar_directa(did, det_cli)

    # Antes: se ve.
    assert _nutricion(client, h_cli)["days"][0]["has_diet"] is True

    assert _modo(client, h_coach, det_cli, "calendario").status_code == 200
    datos = _nutricion(client, h_cli)
    assert not any(d["has_diet"] for d in datos["days"]), \
        "el plan semanal sigue llegando con el calendario activo"
    assert datos.get("nutrition_mode") == "calendario", datos.get("nutrition_mode")


def test_VOLVER_AL_PLAN_SEMANAL_DEVUELVE_LO_QUE_HABIA(client, seed, admin_headers):
    """"No se borra" tiene que ser cierto: si cambiar de modo perdiera el plan,
    la ventana de confirmación estaría mintiendo."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h_coach, f"Semanal {suf}", [
        (f"Pollo {suf}", f"Aves {suf}", 120.0, "g")])
    _asignar_directa(did, det_cli)
    antes = _nutricion(client, h_cli)

    _modo(client, h_coach, det_cli, "calendario")
    _modo(client, h_coach, det_cli, "semanal")

    despues = _nutricion(client, h_cli)
    assert [d["has_diet"] for d in despues["days"]] == [d["has_diet"] for d in antes["days"]]
    comidas = [m["name"] for d in despues["days"] if d["has_diet"] for m in d["meals"]]
    assert comidas and comidas == [m["name"] for d in antes["days"]
                                   if d["has_diet"] for m in d["meals"]]


# ── Y que el calendario llegue ─────────────────────────────────────────────

def test_LAS_DIETAS_DEL_CALENDARIO_LLEGAN_AL_CLIENTE(client, seed, admin_headers):
    """Sin esto, cambiar de modo deja al cliente con la pantalla vacía: se le
    quita el plan semanal y no se le da nada a cambio."""
    suf = uuid.uuid4().hex[:8]
    det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h_coach, f"Del martes {suf}", [
        (f"Salmón {suf}", f"Pescados {suf}", 150.0, "g")])
    _tarea_de_dieta(det_cli, _coach_user_id(det_coach), _lunes() + timedelta(days=1), did)
    _modo(client, h_coach, det_cli, "calendario")

    dias = _nutricion(client, h_cli)["days"]
    assert dias[1]["has_diet"] is True, dias[1]
    assert any(f"Salmón {suf}" == f["name"]
               for m in dias[1]["meals"] for f in m["foods"]), dias[1]["meals"]


def test_un_dia_sin_tarea_es_un_dia_sin_dieta(client, seed, admin_headers):
    """Un hueco visible es mejor que rellenarlo con lo de otro día: el cliente
    tiene que poder preguntar "¿y el miércoles?"."""
    suf = uuid.uuid4().hex[:8]
    det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h_coach, f"Solo lunes {suf}", [
        (f"Avena {suf}", f"Cereales {suf}", 80.0, "g")])
    _tarea_de_dieta(det_cli, _coach_user_id(det_coach), _lunes(), did)
    _modo(client, h_coach, det_cli, "calendario")

    dias = _nutricion(client, h_cli)["days"]
    assert dias[0]["has_diet"] is True
    assert [d["has_diet"] for d in dias[1:]] == [False] * 6, [d["has_diet"] for d in dias]


def test_dos_dietas_el_mismo_dia_no_se_suman(client, seed, admin_headers):
    """Dos tareas el mismo día no significan "come el doble". Se queda la
    primera."""
    suf = uuid.uuid4().hex[:8]
    det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    uid = _coach_user_id(det_coach)
    d1 = _dieta_con(client, h_coach, f"Primera {suf}", [
        (f"Arroz {suf}", f"Cereales {suf}", 100.0, "g")])
    d2 = _dieta_con(client, h_coach, f"Segunda {suf}", [
        (f"Pasta {suf}", f"Cereales {suf}", 100.0, "g")])
    _tarea_de_dieta(det_cli, uid, _lunes(), d1)
    _tarea_de_dieta(det_cli, uid, _lunes(), d2)
    _modo(client, h_coach, det_cli, "calendario")

    comidas = _nutricion(client, h_cli)["days"][0]["meals"]
    alimentos = [f["name"] for m in comidas for f in m["foods"]]
    assert alimentos == [f"Arroz {suf}"], alimentos


def test_una_tarea_de_nutricion_sin_dieta_no_cuenta(client, seed, admin_headers):
    """El calendario admite una nota de nutrición sin dieta enganchada. Eso no
    es un plan: pintarlo como día con dieta dejaría la comida vacía."""
    suf = uuid.uuid4().hex[:8]
    det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    db = SessionLocal()
    try:
        db.add(CalendarTask(
            client_user_detail_id=det_cli, coach_user_id=_coach_user_id(det_coach),
            task_date=_lunes(), task_type="nutricion", title="Beber agua",
            requirements=None))
        db.commit()
    finally:
        db.close()
    _modo(client, h_coach, det_cli, "calendario")

    dias = _nutricion(client, h_cli)["days"]
    assert not any(d["has_diet"] for d in dias), dias[0]


def test_las_tareas_que_no_son_de_nutricion_no_se_cuelan(client, seed, admin_headers):
    """Una rutina en el calendario no es comida."""
    suf = uuid.uuid4().hex[:8]
    det_coach, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h_coach, f"Dieta {suf}", [
        (f"Pan {suf}", f"Cereales {suf}", 60.0, "g")])
    db = SessionLocal()
    try:
        db.add(CalendarTask(
            client_user_detail_id=det_cli, coach_user_id=_coach_user_id(det_coach),
            task_date=_lunes(), task_type="rutina", title="Pierna",
            requirements=json.dumps({"diet_id": did})))
        db.commit()
    finally:
        db.close()
    _modo(client, h_coach, det_cli, "calendario")

    assert not any(d["has_diet"] for d in _nutricion(client, h_cli)["days"])


def test_el_modo_por_defecto_es_el_plan_semanal(client, seed, admin_headers):
    """Nadie cambia de modo por desplegar esto: los clientes que ya existen
    siguen viendo lo suyo."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h_coach, f"Semanal {suf}", [
        (f"Huevo {suf}", f"Huevos {suf}", 2.0, "ud")])
    _asignar_directa(did, det_cli)
    assert _nutricion(client, h_cli)["days"][0]["has_diet"] is True
