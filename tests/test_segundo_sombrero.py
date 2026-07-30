"""El "segundo sombrero": el super-admin puede actuar dentro de una organización.

El documento de jerarquía dibuja a la misma persona como super-admin de la
plataforma Y dueña de NutriEntrena. En el código el super-admin se resolvía
SIEMPRE como plataforma, así que ese segundo sombrero no existía.

Mientras hubo una sola organización daba igual: "toda la plataforma" y "esa
organización" eran el mismo conjunto. Con dos organizaciones los números
divergen — y entonces no había forma de ver la facturación de una sola, ni de
crear contenido privado para su equipo.

Se resuelve con la cabecera `X-Organization-Id`.
"""
from app.database import SessionLocal
from app.models.training import Training

from tests.test_billing_org_scope import _crear_cliente_de
from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _sombrero(org_id):
    return {"X-Organization-Id": org_id}


def _montar_dos_organizaciones(client, admin_headers, sufijo, precio_a, precio_b):
    _uid_a, det_a, _h_a = _crear_usuario(client, admin_headers, f"duenio.{sufijo}.a@nutrientrena-qa.com", role_id=2)
    _uid_b, det_b, _h_b = _crear_usuario(client, admin_headers, f"duenio.{sufijo}.b@nutrientrena-qa.com", role_id=2)
    org_a = _crear_organizacion(det_a, f"Organización {sufijo} A")
    org_b = _crear_organizacion(det_b, f"Organización {sufijo} B")
    _crear_cliente_de(client, admin_headers, det_a, f"Cliente {sufijo} A", precio_a, pagado=0.0)
    _crear_cliente_de(client, admin_headers, det_b, f"Cliente {sufijo} B", precio_b, pagado=0.0)
    return org_a, org_b


# ── El caso que motiva todo esto ────────────────────────────────────────────

def test_el_superadmin_ve_la_facturacion_de_una_organizacion_concreta(client, seed, admin_headers):
    """Con dos organizaciones, "global" ya no vale como "la de NutriEntrena"."""
    org_a, org_b = _montar_dos_organizaciones(client, admin_headers, "sombrero-fact", 111.0, 222.0)

    plataforma = client.get("/api/billing/summary", headers=admin_headers).json()["data"]
    assert plataforma["alcance"] == "plataforma"

    solo_a = client.get("/api/billing/summary", headers={**admin_headers, **_sombrero(org_a)}).json()["data"]
    assert solo_a["alcance"] == "organizacion"
    assert solo_a["organization_id"] == org_a
    assert solo_a["total_facturado"] == 111.0

    solo_b = client.get("/api/billing/summary", headers={**admin_headers, **_sombrero(org_b)}).json()["data"]
    assert solo_b["total_facturado"] == 222.0

    # Y la global sigue sumando las dos (sobre la base compartida entre tests)
    assert plataforma["total_facturado"] >= 333.0


def test_el_superadmin_puede_crear_contenido_privado_de_una_organizacion(client, seed, admin_headers):
    """Sin sombrero crea catálogo de plataforma; con sombrero, contenido
    privado del equipo de esa organización."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.sombrero.contenido@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Organización con contenido del jefe")

    r = client.post("/api/trainings", headers=admin_headers, json={"name": "Ejercicio de fábrica"})
    tid_global = r.json()["data"]["id"]

    r = client.post("/api/trainings", headers={**admin_headers, **_sombrero(org_id)},
                    json={"name": "Ejercicio privado del equipo"})
    tid_org = r.json()["data"]["id"]

    db = SessionLocal()
    try:
        assert db.get(Training, tid_global).organization_id is None
        assert db.get(Training, tid_org).organization_id == org_id
    finally:
        db.close()


def test_las_metricas_tambien_respetan_el_sombrero(client, seed, admin_headers):
    org_a, _org_b = _montar_dos_organizaciones(client, admin_headers, "sombrero-metricas", 10.0, 20.0)

    data = client.get("/api/analytics/overview", headers={**admin_headers, **_sombrero(org_a)}).json()["data"]
    assert data["total_clients"] == 1, data


def test_sin_cabecera_todo_sigue_igual_que_antes(client, seed, admin_headers):
    """Regresión: el sombrero es opcional y no cambia el comportamiento por
    defecto del super-admin."""
    org_a, _org_b = _montar_dos_organizaciones(client, admin_headers, "sombrero-defecto", 5.0, 7.0)

    data = client.get("/api/billing/summary", headers=admin_headers).json()["data"]
    assert data["alcance"] == "plataforma"
    assert data["organization_id"] is None

    # Y sigue viendo el contenido de cualquier organización
    r = client.post("/api/trainings", headers={**admin_headers, **_sombrero(org_a)},
                    json={"name": "Ejercicio para comprobar visibilidad"})
    tid = r.json()["data"]["id"]
    assert client.get(f"/api/trainings/{tid}/edit", headers=admin_headers).status_code == 200


# ── Que la cabecera no sea una escalada de privilegios ──────────────────────

def test_un_coach_no_puede_colarse_en_otra_organizacion_con_la_cabecera(client, seed, admin_headers):
    """La cabecera solo puede confirmar el contexto que ya se tenía."""
    org_a, org_b = _montar_dos_organizaciones(client, admin_headers, "sombrero-escalada", 1.0, 2.0)

    _uid, det, h = _crear_usuario(client, admin_headers, "coach.escalada@nutrientrena-qa.com", role_id=5)
    from tests.test_org_scope import _agregar_miembro
    _agregar_miembro(org_a, det)

    # Su propia organización: la cabecera es redundante pero válida
    assert client.get("/api/trainings/findAll", headers={**h, **_sombrero(org_a)}).status_code == 200

    # La ajena: 403
    r = client.get("/api/trainings/findAll", headers={**h, **_sombrero(org_b)})
    assert r.status_code == 403, r.text


def test_un_admin_duenio_no_puede_saltar_a_otra_organizacion(client, seed, admin_headers):
    org_a, org_b = _montar_dos_organizaciones(client, admin_headers, "sombrero-admin", 3.0, 4.0)

    _uid, det, h = _crear_usuario(client, admin_headers, "admin.no.salta@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det, "Organización del admin que no salta")

    r = client.get("/api/billing/summary", headers={**h, **_sombrero(org_b)})
    assert r.status_code == 403, r.text


def test_una_organizacion_inexistente_da_404(client, seed, admin_headers):
    r = client.get("/api/billing/summary", headers={**admin_headers, **_sombrero("no-existe-esta-id")})
    assert r.status_code == 404, r.text


# ── Descubrimiento de contextos ─────────────────────────────────────────────

def test_el_superadmin_lista_todas_las_organizaciones_disponibles(client, seed, admin_headers):
    org_a, org_b = _montar_dos_organizaciones(client, admin_headers, "sombrero-listado", 1.0, 1.0)

    data = client.get("/api/organizations/switchable", headers=admin_headers).json()["data"]
    assert data["puede_actuar_como_plataforma"] is True
    ids = {o["id"] for o in data["organizaciones"]}
    assert {org_a, org_b} <= ids


def test_un_duenio_solo_se_ve_a_si_mismo(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "duenio.listado@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Organización que solo se ve a sí misma")

    data = client.get("/api/organizations/switchable", headers=h).json()["data"]
    assert data["puede_actuar_como_plataforma"] is False
    assert [o["id"] for o in data["organizaciones"]] == [org_id]
