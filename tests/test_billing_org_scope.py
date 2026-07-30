"""Fase 5b: facturación y métricas por organización.

El documento de jerarquía dice que el dueño de una organización ve la
facturación de SU organización, el super-admin la global, y los coaches del
equipo no ven facturación.

Los datos económicos ya existían por cliente (precio, estado_pago,
importe_pagado…), pero no había vista agregada ninguna. Y analytics.py, que es
lo más parecido a un panel de dirección que había, devolvía SIEMPRE los
totales de toda la plataforma a cualquier admin o coach: su parámetro
`coach_id` es opcional y lo pone quien llama, así que bastaba con no mandarlo.
"""
from app.database import SessionLocal
from app.models.user import User, UserDetail, UserParent

from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _crear_cliente_de(client, headers, coach_detail_id, name, precio, pagado=0.0, estado="pendiente"):
    """Cliente asignado a un coach, con datos de cobro."""
    email = f"{name.lower().replace(' ', '.')}@nutrientrena-qa.com"
    r = client.post("/api/users", headers=headers, json={
        "name": name, "email": email,
        "password": "Cliente123!", "role_id": 6})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        det = db.query(UserDetail).filter(UserDetail.user_id == user.id).first()
        det.precio = precio
        det.importe_pagado = pagado
        det.importe_pendiente = precio - pagado
        det.estado_pago = estado
        db.add(UserParent(user_detail_id=det.id, parent_user_detail_id=coach_detail_id))
        db.commit()
        return det.id
    finally:
        db.close()


def _montar_organizacion(client, admin_headers, sufijo, precios):
    """Crea un dueño de organización con sus clientes de pago."""
    _uid, det, h = _crear_usuario(client, admin_headers, f"duenio.{sufijo}@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, f"Organización {sufijo}")
    for i, precio in enumerate(precios):
        _crear_cliente_de(client, admin_headers, det, f"Cliente {sufijo} {i}", precio, pagado=precio / 2)
    return org_id, det, h


# ── Facturación ─────────────────────────────────────────────────────────────

def test_el_duenio_ve_solo_la_facturacion_de_su_organizacion(client, seed, admin_headers):
    _org_a, _det_a, h_a = _montar_organizacion(client, admin_headers, "factura-a", [100.0, 200.0])
    _org_b, _det_b, h_b = _montar_organizacion(client, admin_headers, "factura-b", [999.0])

    r = client.get("/api/billing/summary", headers=h_a)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["alcance"] == "organizacion"
    assert data["total_facturado"] == 300.0
    assert data["total_cobrado"] == 150.0
    assert data["clientes_de_pago"] == 2

    # Lo de B no se cuela en los totales de A
    r_b = client.get("/api/billing/summary", headers=h_b).json()["data"]
    assert r_b["total_facturado"] == 999.0


def test_el_superadmin_ve_la_facturacion_global(client, seed, admin_headers):
    """La base es compartida entre tests, así que se mide el incremento: lo
    que importa es que suma las dos organizaciones, no una sola."""
    antes = client.get("/api/billing/summary", headers=admin_headers).json()["data"]
    assert antes["alcance"] == "plataforma"

    _montar_organizacion(client, admin_headers, "global-a", [100.0])
    _montar_organizacion(client, admin_headers, "global-b", [250.0])

    despues = client.get("/api/billing/summary", headers=admin_headers).json()["data"]
    assert despues["total_facturado"] - antes["total_facturado"] == 350.0


def test_un_coach_del_equipo_no_ve_facturacion(client, seed, admin_headers):
    """Nivel 3: gestiona sus clientes, pero la facturación no es cosa suya."""
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.sin.factura@nutrientrena-qa.com", role_id=5)
    for ruta in ("/api/billing/summary", "/api/billing/by-coach", "/api/billing/clients"):
        assert client.get(ruta, headers=h).status_code == 403, ruta


def test_un_delegado_que_no_es_duenio_no_ve_facturacion(client, seed, admin_headers):
    """Estar dentro de una organización no basta: la facturación es del dueño."""
    from tests.test_org_scope import _agregar_miembro

    _org_id, _det_duenio, _h = _montar_organizacion(client, admin_headers, "delegado", [500.0])
    _uid, det_delegado, h_delegado = _crear_usuario(client, admin_headers, "delegado.factura@nutrientrena-qa.com", role_id=2)
    _agregar_miembro(_org_id, det_delegado)

    assert client.get("/api/billing/summary", headers=h_delegado).status_code == 403


def test_el_desglose_por_coach_se_queda_en_la_organizacion(client, seed, admin_headers):
    _org_a, det_a, h_a = _montar_organizacion(client, admin_headers, "porcoach-a", [100.0, 300.0])
    _montar_organizacion(client, admin_headers, "porcoach-b", [777.0])

    filas = client.get("/api/billing/by-coach", headers=h_a).json()["data"]
    assert len(filas) == 1
    assert filas[0]["coach_user_detail_id"] == det_a
    assert filas[0]["facturado"] == 400.0
    assert filas[0]["clientes"] == 2


def test_el_listado_por_cliente_se_queda_en_la_organizacion(client, seed, admin_headers):
    _org_a, _det_a, h_a = _montar_organizacion(client, admin_headers, "porcliente-a", [120.0])
    _montar_organizacion(client, admin_headers, "porcliente-b", [888.0])

    filas = client.get("/api/billing/clients", headers=h_a).json()["data"]
    assert [f["precio"] for f in filas] == [120.0]


def test_el_pendiente_se_deduce_si_falta(client, seed, admin_headers):
    """importe_pendiente se rellena a mano y puede quedar desfasado."""
    _uid, det, h = _crear_usuario(client, admin_headers, "duenio.pendiente@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det, "Organización con pendiente sin rellenar")
    cid = _crear_cliente_de(client, admin_headers, det, "Cliente sin pendiente", 200.0, pagado=50.0)

    db = SessionLocal()
    try:
        db.query(UserDetail).filter(UserDetail.id == cid).update({"importe_pendiente": None})
        db.commit()
    finally:
        db.close()

    data = client.get("/api/billing/summary", headers=h).json()["data"]
    assert data["total_pendiente"] == 150.0


# ── Métricas (analytics) ────────────────────────────────────────────────────

def test_las_metricas_ya_no_mezclan_organizaciones(client, seed, admin_headers):
    """El agujero real: sin mandar `coach_id`, cualquier admin veía los
    totales de toda la plataforma."""
    antes = client.get("/api/analytics/overview", headers=admin_headers).json()["data"]

    _org_a, _det_a, h_a = _montar_organizacion(client, admin_headers, "metricas-a", [10.0, 20.0])
    _montar_organizacion(client, admin_headers, "metricas-b", [30.0, 40.0, 50.0])

    # La organización A ve solo los suyos, no los 5
    data = client.get("/api/analytics/overview", headers=h_a).json()["data"]
    assert data["total_clients"] == 2, data

    # El superadmin sí ve los 5 nuevos (sobre la base compartida entre tests)
    despues = client.get("/api/analytics/overview", headers=admin_headers).json()["data"]
    assert despues["total_clients"] - antes["total_clients"] == 5, (antes, despues)


def test_las_metricas_por_coach_se_quedan_en_la_organizacion(client, seed, admin_headers):
    _org_a, det_a, h_a = _montar_organizacion(client, admin_headers, "metricascoach-a", [10.0])
    _montar_organizacion(client, admin_headers, "metricascoach-b", [20.0])

    data = client.get("/api/analytics/coaches", headers=h_a).json()["data"]
    assert {f["coach_id"] for f in data["coaches"]} == {det_a}, data


def test_la_distribucion_por_estado_se_queda_en_la_organizacion(client, seed, admin_headers):
    _org_a, _det_a, h_a = _montar_organizacion(client, admin_headers, "estados-a", [10.0, 20.0])
    _montar_organizacion(client, admin_headers, "estados-b", [30.0, 40.0, 50.0])

    data = client.get("/api/analytics/states", headers=h_a).json()["data"]
    assert data["total"] == 2, data
