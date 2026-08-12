"""Esqueleto del panel de administración de plataforma.

El documento lo describe como una aplicación SEPARADA del panel de coach, con
diez secciones y una navegación que depende del rol del miembro del equipo de
Alzum.

Las secciones las sirve el backend, no el HTML: así el menú de un rol no
depende de que alguien acierte a copiarlo en cada página, y se puede probar
sin navegador.
"""
from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL, SOPORTE
from app.database import SessionLocal
from app.seeds.roles import seed_roles

from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _con_rol(client, admin_headers, email, role_id):
    db = SessionLocal()
    try:
        seed_roles(db)  # idempotente: asegura que existan los roles nuevos
    finally:
        db.close()
    return _crear_usuario(client, admin_headers, email, role_id=role_id)


def _secciones(client, headers):
    r = client.get("/api/admin/me", headers=headers)
    return r.status_code, (r.json().get("data") or {}).get("secciones", []) if r.status_code == 200 else []


# ── Quién entra ────────────────────────────────────────────────────────────

def test_el_superadmin_ve_las_diez_secciones(client, seed, admin_headers):
    codigo, secs = _secciones(client, admin_headers)
    assert codigo == 200
    ids = [s["id"] for s in secs]
    assert ids == ["vision", "organizaciones", "clientes", "facturacion", "planes",
                   "contenido", "soporte", "analiticas", "equipo", "configuracion"], ids


def test_un_coach_no_entra(client, seed, admin_headers):
    """El panel es del equipo de Alzum. Un coach tiene el suyo."""
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.no.admin@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/me", headers=h).status_code == 403


def test_un_cliente_no_entra(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "cliente.no.admin@nutrientrena-qa.com", role_id=6)
    assert client.get("/api/admin/me", headers=h).status_code == 403


def test_sin_sesion_no_entra(client, seed):
    assert client.get("/api/admin/me").status_code in (401, 403)


# ── Qué ve cada miembro del equipo ─────────────────────────────────────────

def test_el_editor_de_contenido_solo_ve_su_seccion(client, seed, admin_headers):
    """El documento es explícito: "un editor de contenido global entra y solo
    ve Contenido global en su sidebar, nada más"."""
    _uid, _det, h = _con_rol(client, admin_headers, "editor.panel@nutrientrena-qa.com", EDITOR_CONTENIDO_GLOBAL)
    codigo, secs = _secciones(client, h)
    assert codigo == 200
    assert [s["id"] for s in secs] == ["contenido"]


def test_soporte_ve_lo_suyo_y_no_la_facturacion(client, seed, admin_headers):
    """"Solo accede a Soporte y a ver organizaciones, sin tocar facturación"."""
    _uid, _det, h = _con_rol(client, admin_headers, "soporte.panel@nutrientrena-qa.com", SOPORTE)
    codigo, secs = _secciones(client, h)
    assert codigo == 200
    ids = [s["id"] for s in secs]
    assert "soporte" in ids and "organizaciones" in ids and "clientes" in ids
    assert "facturacion" not in ids and "planes" not in ids
    assert "equipo" not in ids and "configuracion" not in ids


def test_el_orden_de_las_secciones_es_el_del_documento(client, seed, admin_headers):
    """Aunque el rol vea un subconjunto, el orden se respeta: es el del
    sidebar descrito en el documento."""
    _uid, _det, h = _con_rol(client, admin_headers, "soporte.orden@nutrientrena-qa.com", SOPORTE)
    _codigo, secs = _secciones(client, h)
    assert [s["id"] for s in secs] == ["organizaciones", "clientes", "soporte"]


# ── Selector de contexto ───────────────────────────────────────────────────

def test_el_superadmin_puede_saltar_a_cualquier_organizacion(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.panel@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Organización del panel")

    d = client.get("/api/admin/me", headers=admin_headers).json()["data"]
    assert org_id in [o["id"] for o in d["organizaciones"]]
    assert d["es_superadmin"] is True


def test_el_equipo_interno_no_salta_a_organizaciones(client, seed, admin_headers):
    """Soporte y el editor no tienen panel de coach al que ir: el selector no
    debe ofrecerles organizaciones."""
    _uid, _det, h = _con_rol(client, admin_headers, "soporte.sin.orgs@nutrientrena-qa.com", SOPORTE)
    d = client.get("/api/admin/me", headers=h).json()["data"]
    assert d["organizaciones"] == []
    assert d["es_superadmin"] is False


# ── El panel se sirve ──────────────────────────────────────────────────────

def test_el_panel_se_sirve_y_la_ruta_admin_redirige(client, seed):
    assert client.get("/app/admin/index.html").status_code == 200
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "/app/admin/" in r.headers.get("location", "")


# ── Cuentas: dar de alta entrenadores manualmente ───────────────────────────
# Es lo que pedía el cliente para cerrar la fase. Antes NO se podía: POST
# /organizations fijaba el dueño como quien llamaba, así que no había forma de
# crear un centro para otra persona.

def _crear_cuenta(client, headers, **datos):
    return client.post("/api/admin/organizations", headers=headers, json=datos)


def test_el_superadmin_da_de_alta_una_cuenta_con_dueno_nuevo(client, seed, admin_headers):
    r = _crear_cuenta(client, admin_headers, name="NutriEntrena",
                      country="España", owner_name="Oswal Serrano",
                      owner_email="oswal.centro@nutrientrena-qa.com",
                      owner_password="Centro123!")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["name"] == "NutriEntrena"
    assert d["owner_name"] == "Oswal Serrano"
    assert d["owner_email"] == "oswal.centro@nutrientrena-qa.com"
    assert d["state"] == "activa"
    assert d["coaches"] >= 1


def test_el_dueno_creado_puede_entrar_y_su_contenido_es_de_su_cuenta(client, seed, admin_headers):
    """Lo importante del alta: que el entrenador quede DENTRO de su cuenta.
    Sin organización, su contenido se publicaba en el catálogo de plataforma y
    lo veía todo el mundo."""
    from app.core.security import create_access_token
    from app.database import SessionLocal
    from app.models.user import User

    r = _crear_cuenta(client, admin_headers, name="Centro Con Dueño",
                      owner_name="Marta Ruiz", owner_email="marta.centro@nutrientrena-qa.com",
                      owner_password="Centro123!")
    org_id = r.json()["data"]["id"]

    db = SessionLocal()
    try:
        uid = db.query(User).filter(User.email == "marta.centro@nutrientrena-qa.com").first().id
    finally:
        db.close()
    h = {"Authorization": f"Bearer {create_access_token({'sub': str(uid)})}"}

    rr = client.post("/api/routines", headers=h, json={"name": "Rutina de Marta"})
    assert rr.status_code == 200, rr.text
    assert rr.json()["data"]["organization_id"] == org_id, "debería quedar en su cuenta, no global"


def test_se_puede_asignar_un_usuario_existente_como_dueno(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.ya.existe@nutrientrena-qa.com", role_id=5)
    r = _crear_cuenta(client, admin_headers, name="Centro de alguien que ya estaba",
                      owner_user_detail_id=det)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["owner_user_detail_id"] == det


def test_no_se_puede_poner_dos_veces_al_mismo_dueno(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.doble.cuenta@nutrientrena-qa.com", role_id=5)
    assert _crear_cuenta(client, admin_headers, name="Primera", owner_user_detail_id=det).status_code == 200
    r = _crear_cuenta(client, admin_headers, name="Segunda", owner_user_detail_id=det)
    assert r.status_code == 400, r.text


def test_validaciones_del_alta(client, seed, admin_headers):
    assert _crear_cuenta(client, admin_headers, name="").status_code == 400
    assert _crear_cuenta(client, admin_headers, name="Sin dueño").status_code == 400
    assert _crear_cuenta(client, admin_headers, name="Estado raro", state="inventado",
                         owner_name="X", owner_email="x.raro@nutrientrena-qa.com",
                         owner_password="Clave123!").status_code == 400
    assert _crear_cuenta(client, admin_headers, name="Clave corta", owner_name="Y",
                         owner_email="y.corta@nutrientrena-qa.com", owner_password="123").status_code == 400


def test_soporte_ve_las_cuentas_pero_no_las_crea(client, seed, admin_headers):
    _uid, _det, h = _con_rol(client, admin_headers, "soporte.cuentas@nutrientrena-qa.com", SOPORTE)
    assert client.get("/api/admin/organizations", headers=h).status_code == 200
    assert _crear_cuenta(client, h, name="Intento de soporte",
                         owner_name="Z", owner_email="z.soporte@nutrientrena-qa.com",
                         owner_password="Clave123!").status_code == 403


def test_un_coach_no_ve_las_cuentas(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.sin.panel.cuentas@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/organizations", headers=h).status_code == 403


# ── Estados ────────────────────────────────────────────────────────────────

def test_suspender_y_reactivar_una_cuenta(client, seed, admin_headers):
    from app.database import SessionLocal
    from app.models.organization import Organization

    org_id = _crear_cuenta(client, admin_headers, name="Centro que se suspende",
                           owner_name="Nico Paz", owner_email="nico.susp@nutrientrena-qa.com",
                           owner_password="Centro123!").json()["data"]["id"]

    r = client.put(f"/api/admin/organizations/{org_id}/state", headers=admin_headers, json={"state": "suspendida"})
    assert r.status_code == 200 and r.json()["data"]["state"] == "suspendida"

    db = SessionLocal()
    try:
        assert db.get(Organization, org_id).is_active is False, "is_active debe seguir en sincronía"
    finally:
        db.close()

    r = client.put(f"/api/admin/organizations/{org_id}/state", headers=admin_headers, json={"state": "activa"})
    assert r.status_code == 200 and r.json()["data"]["state"] == "activa"
    db = SessionLocal()
    try:
        assert db.get(Organization, org_id).is_active is True
    finally:
        db.close()


def test_un_coach_no_puede_cambiar_estados(client, seed, admin_headers):
    org_id = _crear_cuenta(client, admin_headers, name="Centro intocable",
                           owner_name="Ana", owner_email="ana.estado@nutrientrena-qa.com",
                           owner_password="Centro123!").json()["data"]["id"]
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.cambia.estado@nutrientrena-qa.com", role_id=5)
    assert client.put(f"/api/admin/organizations/{org_id}/state", headers=h, json={"state": "suspendida"}).status_code == 403


# ── Red de seguridad ───────────────────────────────────────────────────────

def test_detecta_entrenadores_sin_cuenta(client, seed, admin_headers):
    """Un coach sin organización publica su contenido en el catálogo de
    plataforma: lo ve toda organización. Hay que poder verlos."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "coach.huerfano@nutrientrena-qa.com", role_id=5)

    sueltos = client.get("/api/admin/coaches-sin-cuenta", headers=admin_headers).json()["data"]
    assert det in [s["user_detail_id"] for s in sueltos], sueltos

    # Al darle una cuenta, desaparece de la lista
    _crear_cuenta(client, admin_headers, name="Cuenta del huérfano", owner_user_detail_id=det)
    sueltos = client.get("/api/admin/coaches-sin-cuenta", headers=admin_headers).json()["data"]
    assert det not in [s["user_detail_id"] for s in sueltos]


# ── Lo que no se inventa ───────────────────────────────────────────────────

def test_plan_e_importe_llegan_vacios_a_proposito(client, seed, admin_headers):
    """Dependen de la pasarela de pago, que está fuera de alcance. Se
    devuelven en null para que la pantalla los muestre como "—" en vez de
    parecer que ya funcionan."""
    d = _crear_cuenta(client, admin_headers, name="Centro sin plan",
                      owner_name="Sara", owner_email="sara.plan@nutrientrena-qa.com",
                      owner_password="Centro123!").json()["data"]
    assert d["plan"] is None and d["mrr"] is None
