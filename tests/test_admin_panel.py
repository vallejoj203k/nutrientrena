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
