"""Sección "Clientes finales" del panel de plataforma.

Es una vista de SOLO LECTURA, y deliberadamente pobre en datos. Un cliente
final no es cliente de Alzum: es cliente de su coach. Desde el panel se ve
quién es, de qué cuenta y en qué estado —lo justo para dar soporte— y nada de
peso, medidas, fotos ni patologías.

Estas pruebas cubren las dos cosas que pueden salir mal:
- que se filtre lo íntimo (o que aparezca un endpoint para editarlo);
- que la atribución a la cuenta sea incorrecta, que es de lo que depende que
  el filtro "Todas las cuentas" signifique algo.
"""
from datetime import date, timedelta

from app.core.dependencies import SOPORTE
from app.database import SessionLocal
from app.models.checkin import WeeklyCheckin
from app.models.session_log import WorkoutSession
from app.models.user import User, UserDetail, UserParent

from tests.test_admin_panel import _con_rol
from tests.test_org_scope import _agregar_miembro, _crear_organizacion, _crear_usuario


def _crear_cliente(client, headers, coach_detail_id, name, estado="activo"):
    email = f"{name.lower().replace(' ', '.')}@nutrientrena-qa.com"
    r = client.post("/api/users", headers=headers, json={
        "name": name, "email": email, "password": "Cliente123!", "role_id": 6})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        det = db.query(UserDetail).filter(UserDetail.user_id == user.id).first()
        det.lifecycle_status = estado
        db.add(UserParent(user_detail_id=det.id, parent_user_detail_id=coach_detail_id))
        db.commit()
        return det.id
    finally:
        db.close()


def _listar(client, headers):
    r = client.get("/api/admin/clients", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _fila(datos, detail_id):
    return next((c for c in datos["clientes"] if c["user_detail_id"] == detail_id), None)


# ── Quién puede mirar ───────────────────────────────────────────────────────

def test_el_superadmin_ve_los_clientes_de_toda_la_plataforma(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.plat@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro con clientes visibles")
    cid = _crear_cliente(client, admin_headers, det, "Laura Visible")

    assert _fila(_listar(client, admin_headers), cid) is not None


def test_soporte_tambien_puede_verlos(client, seed, admin_headers):
    """El documento le da la sección: sin ella no puede atender a nadie."""
    _uid, _det, h = _con_rol(client, admin_headers, "soporte.clientes@nutrientrena-qa.com", SOPORTE)
    assert client.get("/api/admin/clients", headers=h).status_code == 200


def test_un_coach_no_entra_al_listado_de_plataforma(client, seed, admin_headers):
    """Vería los clientes de sus competidores."""
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.cli.fuera@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/clients", headers=h).status_code == 403


def test_un_cliente_tampoco(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "cliente.cli.fuera@nutrientrena-qa.com", role_id=6)
    assert client.get("/api/admin/clients", headers=h).status_code == 403


# ── Lo que NO se enseña ─────────────────────────────────────────────────────

def test_no_se_filtran_medidas_ni_fotos_ni_patologias(client, seed, admin_headers):
    """La línea entre dar soporte y leer el historial médico de alguien que no
    te lo ha dado a ti. Si algún día se añade un campo al serializador, esta
    prueba lo caza."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.intimo@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro con datos íntimos")
    cid = _crear_cliente(client, admin_headers, det, "Iván Privado")

    db = SessionLocal()
    try:
        d = db.query(UserDetail).filter(UserDetail.id == cid).first()
        d.weight, d.height, d.body_fat = 82.5, 178.0, 19.0
        d.photo = "https://ejemplo/foto.jpg"
        d.allergies, d.injuries = "frutos secos", "hombro derecho"
        db.commit()
    finally:
        db.close()

    fila = _fila(_listar(client, admin_headers), cid)
    permitidas = {"user_detail_id", "name", "email", "coach_name", "organization_id",
                  "organization_name", "state", "created_at", "last_activity"}
    assert set(fila) == permitidas, set(fila) - permitidas
    plano = str(fila)
    for filtrado in ["82.5", "178", "19.0", "foto.jpg", "frutos secos", "hombro"]:
        assert filtrado not in plano, (filtrado, plano)


def test_no_hay_forma_de_editar_al_cliente_desde_el_panel(client, seed, admin_headers):
    """Solo lectura de verdad, no solo en la pantalla."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.solo.lectura@nutrientrena-qa.com", role_id=5)
    cid = _crear_cliente(client, admin_headers, det, "Carmen Intocable")

    for metodo, ruta in [("PUT", f"/api/admin/clients/{cid}"),
                         ("DELETE", f"/api/admin/clients/{cid}"),
                         ("POST", "/api/admin/clients")]:
        r = client.request(metodo, ruta, headers=admin_headers, json={"name": "Cambiado"})
        assert r.status_code in (404, 405), (metodo, ruta, r.status_code)


# ── Atribución a la cuenta ──────────────────────────────────────────────────

def test_el_cliente_se_atribuye_a_la_cuenta_de_su_coach(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.cuenta@nutrientrena-qa.com", role_id=5)
    org_id = _crear_organizacion(det, "Centro Atribución")
    cid = _crear_cliente(client, admin_headers, det, "Diego Atribuido")

    fila = _fila(_listar(client, admin_headers), cid)
    assert fila["organization_id"] == org_id
    assert fila["organization_name"] == "Centro Atribución"
    assert fila["coach_name"].startswith("coach.cli.cuenta") or fila["coach_name"]


def test_el_cliente_de_un_coach_del_equipo_cuenta_para_la_organizacion(client, seed, admin_headers):
    """Los clientes no cuelgan de la organización: cuelgan de un coach. Si la
    atribución solo mirase al dueño, los del resto del equipo saldrían "sin
    cuenta" y el filtro por cuenta mentiría."""
    _uid_d, det_d, _h = _crear_usuario(client, admin_headers, "duenio.cli.equipo@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det_d, "Centro con equipo")
    _uid_c, det_c, _hc = _crear_usuario(client, admin_headers, "coach.cli.equipo@nutrientrena-qa.com", role_id=5)
    _agregar_miembro(org_id, det_c)

    cid = _crear_cliente(client, admin_headers, det_c, "Paula De Equipo")
    fila = _fila(_listar(client, admin_headers), cid)
    assert fila["organization_id"] == org_id, fila


def test_el_cliente_de_un_coach_suelto_sale_sin_cuenta(client, seed, admin_headers):
    """Y se dice, en vez de colgarlo de una organización cualquiera."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.suelto@nutrientrena-qa.com", role_id=5)
    cid = _crear_cliente(client, admin_headers, det, "Hugo Sin Cuenta")

    fila = _fila(_listar(client, admin_headers), cid)
    assert fila["organization_id"] is None and fila["organization_name"] is None, fila


# ── Estado y actividad ──────────────────────────────────────────────────────

def test_el_estado_es_el_ciclo_de_vida_que_ya_usa_el_coach(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.estados@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro de estados")
    activo = _crear_cliente(client, admin_headers, det, "Ana Activa", estado="activo")
    pausado = _crear_cliente(client, admin_headers, det, "Beto Pausado", estado="pausado")
    fin = _crear_cliente(client, admin_headers, det, "Clara Finalizada", estado="finalizado")

    datos = _listar(client, admin_headers)
    assert _fila(datos, activo)["state"] == "activo"
    assert _fila(datos, pausado)["state"] == "pausado"
    assert _fila(datos, fin)["state"] == "finalizado"
    assert datos["totales"]["total"] >= 3
    assert datos["totales"]["activos"] >= 1
    assert datos["totales"]["finalizados"] >= 1


def test_la_ultima_actividad_es_lo_ultimo_que_hizo_el_cliente(client, seed, admin_headers):
    """No lo que le puso el coach: un entrenamiento registrado o un check-in.
    Y de varias señales gana la más reciente."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.actividad@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro con actividad")
    cid = _crear_cliente(client, admin_headers, det, "Marta Activa")

    hoy = date.today()
    db = SessionLocal()
    try:
        db.add(WeeklyCheckin(client_user_detail_id=cid, checkin_date=hoy - timedelta(days=9)))
        db.add(WorkoutSession(client_user_detail_id=cid, session_date=hoy - timedelta(days=2)))
        db.commit()
    finally:
        db.close()

    fila = _fila(_listar(client, admin_headers), cid)
    assert fila["last_activity"] == (hoy - timedelta(days=2)).isoformat(), fila


def test_sin_actividad_se_dice_en_vez_de_inventar_una_fecha(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.inactivo@nutrientrena-qa.com", role_id=5)
    cid = _crear_cliente(client, admin_headers, det, "Nuria Callada")

    assert _fila(_listar(client, admin_headers), cid)["last_activity"] is None


def test_un_cliente_dado_de_baja_no_aparece(client, seed, admin_headers):
    """La baja es reversible y conserva el historial, pero el cliente ya no
    está: si saliera aquí, los totales de la plataforma serían falsos."""
    from datetime import datetime

    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.cli.baja@nutrientrena-qa.com", role_id=5)
    cid = _crear_cliente(client, admin_headers, det, "Sergio De Baja")
    assert _fila(_listar(client, admin_headers), cid) is not None

    db = SessionLocal()
    try:
        d = db.query(UserDetail).filter(UserDetail.id == cid).first()
        d.deleted_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

    assert _fila(_listar(client, admin_headers), cid) is None
