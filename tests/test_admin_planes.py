"""Sección "Planes": lo que un coach le paga a Alzum.

Ojo con el nombre. En este código "plan" ya significaba otra cosa —el envío de
una dieta y una rutina a un cliente, PlanDelivery—. Aquí se habla de la tarifa.
Las dos se llaman igual en castellano y se confunden solas.

Esto es el CATÁLOGO, no la facturación: definir cuánto cuesta el plan Pro no
necesita pasarela de pago; cobrarlo sí, y eso sigue fuera de alcance. Por eso
el MRR sigue en null aunque ya se pueda asignar un plan a una cuenta: el plan
dice lo que DEBERÍA pagar, no lo que ha pagado.
"""
from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL, SOPORTE
from app.database import SessionLocal
from app.models.organization import Organization

from tests.test_admin_panel import _con_rol, _crear_cuenta
from tests.test_org_scope import _crear_organizacion, _crear_usuario

PRO = {
    "name": "Pro",
    "price_month": 49,
    "price_year_month": 39,
    "default_cycle": "mensual",
    "max_clients": 50,
    "coaches_included": 1,
    "extra_coach_price": 15,
    "storage": "50 GB",
    "support": "Prioritario < 24 h",
    "features": "Todo lo de Starter\nAutomatizaciones y recordatorios\nMarca propia / app personalizada",
    "visible": True,
    "highlighted": True,
}


def _planes(client, headers):
    r = client.get("/api/admin/plans", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _crear(client, headers, **cambios):
    return client.post("/api/admin/plans", headers=headers, json={**PRO, **cambios})


def _por_nombre(datos, nombre):
    return next((p for p in datos["planes"] if p["name"] == nombre), None)


# ── Quién entra ─────────────────────────────────────────────────────────────

def test_solo_el_superadmin_toca_los_planes(client, seed, admin_headers):
    assert client.get("/api/admin/plans", headers=admin_headers).status_code == 200

    for email, rol in [("soporte.pl@nutrientrena-qa.com", SOPORTE),
                       ("editor.pl@nutrientrena-qa.com", EDITOR_CONTENIDO_GLOBAL)]:
        _uid, _det, h = _con_rol(client, admin_headers, email, rol)
        assert client.get("/api/admin/plans", headers=h).status_code == 403
        assert _crear(client, h, name="Colado").status_code == 403

    _uid, _det, hc = _crear_usuario(client, admin_headers, "coach.pl@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/plans", headers=hc).status_code == 403


# ── Crear ───────────────────────────────────────────────────────────────────

def test_crear_un_plan_con_todos_los_datos_del_formulario(client, seed, admin_headers):
    r = _crear(client, admin_headers, name="Pro QA")
    assert r.status_code == 200, r.text
    d = r.json()["data"]

    assert d["name"] == "Pro QA"
    assert d["price_month"] == 49 and d["price_year_month"] == 39
    assert d["max_clients"] == 50 and d["coaches_included"] == 1
    assert d["extra_coach_price"] == 15
    assert d["storage"] == "50 GB" and d["support"] == "Prioritario < 24 h"
    assert d["highlighted"] is True and d["visible"] is True
    # Las funcionalidades entran como texto de varias líneas y salen como lista
    assert d["features"] == ["Todo lo de Starter", "Automatizaciones y recordatorios",
                             "Marca propia / app personalizada"]
    # Y nace sin cuentas dentro
    assert d["cuentas"] == 0


def test_el_descuento_anual_se_calcula_no_se_guarda(client, seed, admin_headers):
    """Guardarlo sería un tercer número que se puede quedar sin cuadrar con los
    otros dos."""
    d = _crear(client, admin_headers, name="Starter QA",
               price_month=19, price_year_month=15).json()["data"]
    assert d["descuento_anual"] == 21, d      # 1 - 15/19

    # Sin precio anual no hay descuento que enseñar
    gratis = _crear(client, admin_headers, name="Gratis QA",
                    price_month=0, price_year_month=None).json()["data"]
    assert gratis["descuento_anual"] is None


def test_cero_clientes_significa_ilimitado(client, seed, admin_headers):
    """Se usa el cero y no null para que "ilimitado" sea una decisión escrita y
    no un campo que alguien se dejó vacío."""
    d = _crear(client, admin_headers, name="Business QA", max_clients=0).json()["data"]
    assert d["max_clients"] == 0


def test_no_se_repite_el_nombre_de_un_plan(client, seed, admin_headers):
    _crear(client, admin_headers, name="Repetido QA")
    assert _crear(client, admin_headers, name="Repetido QA").status_code == 400


def test_un_plan_necesita_nombre(client, seed, admin_headers):
    assert _crear(client, admin_headers, name="   ").status_code == 400


def test_no_se_admiten_precios_negativos_ni_ciclos_inventados(client, seed, admin_headers):
    assert _crear(client, admin_headers, name="Negativo QA", price_month=-5).status_code == 400
    assert _crear(client, admin_headers, name="Negativo2 QA", extra_coach_price=-1).status_code == 400
    assert _crear(client, admin_headers, name="Clientes QA", max_clients=-3).status_code == 400
    assert _crear(client, admin_headers, name="Ciclo QA", default_cycle="semanal").status_code == 400


def test_pagar_al_ano_no_puede_salir_mas_caro_que_al_mes(client, seed, admin_headers):
    """No es un plan: es una errata. Cuesta más descubrirla en la web de precios
    que negarla aquí."""
    r = _crear(client, admin_headers, name="Al revés QA", price_month=19, price_year_month=29)
    assert r.status_code == 400, r.text


# ── Editar, ocultar, borrar ─────────────────────────────────────────────────

def test_editar_un_plan(client, seed, admin_headers):
    pid = _crear(client, admin_headers, name="Editable QA").json()["data"]["id"]
    r = client.put(f"/api/admin/plans/{pid}", headers=admin_headers,
                   json={**PRO, "name": "Editado QA", "price_month": 59,
                         "features": "Solo una cosa"})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["name"] == "Editado QA" and d["price_month"] == 59
    assert d["features"] == ["Solo una cosa"]


def test_ocultar_no_es_borrar(client, seed, admin_headers):
    """Un plan retirado de la web sigue teniendo cuentas dentro que lo pagan."""
    pid = _crear(client, admin_headers, name="Ocultable QA").json()["data"]["id"]

    r = client.put(f"/api/admin/plans/{pid}/visibility", headers=admin_headers,
                   json={"visible": False})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["visible"] is False
    # Sigue existiendo y sigue listándose en el panel
    assert _por_nombre(_planes(client, admin_headers), "Ocultable QA") is not None

    client.put(f"/api/admin/plans/{pid}/visibility", headers=admin_headers, json={"visible": True})
    assert _por_nombre(_planes(client, admin_headers), "Ocultable QA")["visible"] is True


def test_un_plan_sin_cuentas_se_puede_borrar(client, seed, admin_headers):
    pid = _crear(client, admin_headers, name="Borrable QA").json()["data"]["id"]
    assert client.delete(f"/api/admin/plans/{pid}", headers=admin_headers).status_code == 200
    assert _por_nombre(_planes(client, admin_headers), "Borrable QA") is None


def test_no_se_borra_un_plan_que_alguien_tiene_contratado(client, seed, admin_headers):
    """Dejaría a esas cuentas sin plan y sin rastro de cuál tenían."""
    pid = _crear(client, admin_headers, name="Con cuentas QA").json()["data"]["id"]
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.pl.borrar@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro con plan contratado")
    assert client.put(f"/api/admin/organizations/{org_id}/plan", headers=admin_headers,
                      json={"plan_id": pid}).status_code == 200

    r = client.delete(f"/api/admin/plans/{pid}", headers=admin_headers)
    assert r.status_code == 400, r.text
    assert "ocúltalo" in r.json()["message"].lower()


# ── Asignar a una cuenta ────────────────────────────────────────────────────

def test_asignar_un_plan_y_que_el_contador_lo_note(client, seed, admin_headers):
    """Sin la asignación, el "N cuentas" de cada tarjeta sería siempre cero: un
    número muerto en una pantalla que existe para decidir precios."""
    pid = _crear(client, admin_headers, name="Contado QA").json()["data"]["id"]
    assert _por_nombre(_planes(client, admin_headers), "Contado QA")["cuentas"] == 0

    d = _crear_cuenta(client, admin_headers, name="Centro que contrata",
                      owner_name="Contrata Dueño", owner_email="contrata@nutrientrena-qa.com",
                      owner_password="Centro123!").json()["data"]

    r = client.put(f"/api/admin/organizations/{d['id']}/plan", headers=admin_headers,
                   json={"plan_id": pid})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["plan"] == "Contado QA"

    assert _por_nombre(_planes(client, admin_headers), "Contado QA")["cuentas"] == 1

    # Y el listado de Coaches ya enseña el plan
    cuentas = client.get("/api/admin/organizations", headers=admin_headers).json()["data"]["cuentas"]
    fila = next(c for c in cuentas if c["id"] == d["id"])
    assert fila["plan"] == "Contado QA" and fila["plan_id"] == pid


def test_se_puede_retirar_el_plan_de_una_cuenta(client, seed, admin_headers):
    pid = _crear(client, admin_headers, name="Retirable QA").json()["data"]["id"]
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.pl.retira@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro que se queda sin plan")

    client.put(f"/api/admin/organizations/{org_id}/plan", headers=admin_headers, json={"plan_id": pid})
    r = client.put(f"/api/admin/organizations/{org_id}/plan", headers=admin_headers, json={"plan_id": None})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["plan"] is None

    db = SessionLocal()
    try:
        assert db.query(Organization).filter(Organization.id == org_id).first().plan_id is None
    finally:
        db.close()


def test_no_se_asigna_un_plan_que_no_existe(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.pl.fantasma@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro con plan fantasma")
    assert client.put(f"/api/admin/organizations/{org_id}/plan", headers=admin_headers,
                      json={"plan_id": 999999}).status_code == 404


def test_una_cuenta_que_no_existe_da_404(client, seed, admin_headers):
    pid = _crear(client, admin_headers, name="Sin cuenta QA").json()["data"]["id"]
    assert client.put("/api/admin/organizations/no-existe/plan", headers=admin_headers,
                      json={"plan_id": pid}).status_code == 404


# ── Lo que sigue sin inventarse ─────────────────────────────────────────────

def test_el_mrr_sigue_en_null_aunque_haya_planes_asignados(client, seed, admin_headers):
    """Un plan asignado dice lo que la cuenta DEBERÍA pagar, no lo que ha
    pagado. Sumar tarifas y llamarlo MRR sería enseñar ingresos que nadie ha
    cobrado."""
    pid = _crear(client, admin_headers, name="MRR QA", price_month=99).json()["data"]["id"]
    d = _crear_cuenta(client, admin_headers, name="Centro de pago",
                      owner_name="Pago Dueño", owner_email="pago.duenio@nutrientrena-qa.com",
                      owner_password="Centro123!").json()["data"]
    client.put(f"/api/admin/organizations/{d['id']}/plan", headers=admin_headers, json={"plan_id": pid})

    cuentas = client.get("/api/admin/organizations", headers=admin_headers).json()["data"]["cuentas"]
    fila = next(c for c in cuentas if c["id"] == d["id"])
    assert fila["plan"] == "MRR QA"
    assert fila["mrr"] is None

    assert client.get("/api/admin/analytics", headers=admin_headers).json()["data"]["kpis"]["mrr"] is None


def test_los_totales_cuentan_las_que_todavia_no_tienen_plan(client, seed, admin_headers):
    """Es el número que dice cuánto trabajo queda por hacer."""
    t = _planes(client, admin_headers)["totales"]
    cuentas = client.get("/api/admin/organizations", headers=admin_headers).json()["data"]["totales"]["cuentas"]
    assert t["cuentas_con_plan"] + t["cuentas_sin_plan"] == cuentas


# ── Ficha de la cuenta ──────────────────────────────────────────────────────

def test_la_ficha_se_guarda_entera_de_una_vez(client, seed, admin_headers):
    """Con un endpoint por campo, cambiar plan y estado a la vez serían dos
    peticiones y media ficha podría quedarse guardada si la segunda falla."""
    pid = _crear(client, admin_headers, name="Ficha QA").json()["data"]["id"]
    d = _crear_cuenta(client, admin_headers, name="Centro de la ficha",
                      owner_name="Ficha Dueño", owner_email="ficha.duenio@nutrientrena-qa.com",
                      owner_password="Centro123!").json()["data"]

    r = client.put(f"/api/admin/organizations/{d['id']}", headers=admin_headers, json={
        "state": "prueba", "plan_id": pid, "internal_notes": "Cuenta demo interna."})
    assert r.status_code == 200, r.text
    g = r.json()["data"]
    assert g["state"] == "prueba"
    assert g["plan"] == "Ficha QA"
    assert g["internal_notes"] == "Cuenta demo interna."
    # Y la cuota sale del plan
    assert g["cuota_mes"] == 49


def test_quitar_el_plan_desde_la_ficha_se_distingue_de_no_tocarlo(client, seed, admin_headers):
    """Un null a secas no distingue "quítaselo" de "no lo cambies"; por eso hay
    un centinela."""
    pid = _crear(client, admin_headers, name="Centinela QA").json()["data"]["id"]
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.pl.centinela@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro del centinela")
    client.put(f"/api/admin/organizations/{org_id}", headers=admin_headers, json={"plan_id": pid})

    # Guardar solo las notas NO le quita el plan
    r = client.put(f"/api/admin/organizations/{org_id}", headers=admin_headers,
                   json={"internal_notes": "Solo una nota"})
    assert r.json()["data"]["plan"] == "Centinela QA", r.text

    # Con el centinela sí
    r = client.put(f"/api/admin/organizations/{org_id}", headers=admin_headers,
                   json={"quitar_plan": True})
    assert r.json()["data"]["plan"] is None, r.text


def test_las_notas_internas_no_salen_por_el_lado_del_coach(client, seed, admin_headers):
    """Son notas del equipo de Alzum SOBRE la cuenta. Que las viera el coach
    sería peor que no tenerlas."""
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.notas@nutrientrena-qa.com", role_id=5)
    org_id = _crear_organizacion(det, "Centro con notas")
    client.put(f"/api/admin/organizations/{org_id}", headers=admin_headers,
               json={"internal_notes": "Ojo: pidió descuento"})

    # El coach no entra al panel de plataforma
    assert client.get(f"/api/admin/organizations/{org_id}", headers=h).status_code == 403
    # Y su propia organización no se las devuelve
    r = client.get("/api/organizations/switchable", headers=h)
    assert "descuento" not in r.text


def test_un_estado_inventado_no_se_guarda_desde_la_ficha(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.pl.estado@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro con estado raro")
    assert client.put(f"/api/admin/organizations/{org_id}", headers=admin_headers,
                      json={"state": "zombi"}).status_code == 400


def test_suspender_desde_la_ficha_desactiva_la_cuenta(client, seed, admin_headers):
    """is_active se mantiene en sincronía: hay código antiguo que lo consulta."""
    from app.models.organization import Organization as _Org

    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.pl.susp@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro que se suspende desde la ficha")
    client.put(f"/api/admin/organizations/{org_id}", headers=admin_headers, json={"state": "suspendida"})

    db = SessionLocal()
    try:
        assert db.query(_Org).filter(_Org.id == org_id).first().is_active is False
    finally:
        db.close()


def test_la_ultima_actividad_de_una_cuenta_mira_al_equipo_y_a_sus_clientes(client, seed, admin_headers):
    """Con solo los accesos del coach, una cuenta cuyo dueño entra a diario
    parecería viva aunque nadie entrene; con solo la actividad de los clientes,
    un centro que acaba de empezar parecería muerto."""
    d = _crear_cuenta(client, admin_headers, name="Centro recién nacido",
                      owner_name="Nuevo Dueño", owner_email="nuevo.duenio@nutrientrena-qa.com",
                      owner_password="Centro123!").json()["data"]

    # Nadie ha entrado todavía
    ficha = client.get(f"/api/admin/organizations/{d['id']}", headers=admin_headers).json()["data"]
    assert ficha["last_activity"] is None, ficha

    # El dueño entra: ya hay actividad, aunque no tenga ni un cliente
    client.post("/api/auth/login", json={"email": "nuevo.duenio@nutrientrena-qa.com",
                                         "password": "Centro123!"})
    ficha = client.get(f"/api/admin/organizations/{d['id']}", headers=admin_headers).json()["data"]
    assert ficha["last_activity"] is not None, ficha


def test_la_cuota_contratada_suma_solo_las_cuentas_activas(client, seed, admin_headers):
    """Una cuenta suspendida no paga. Sumarla inflaría el número justo cuando
    más importa que sea verdad."""
    pid = _crear(client, admin_headers, name="Suma QA", price_month=100).json()["data"]["id"]
    d = _crear_cuenta(client, admin_headers, name="Centro que se cae de la suma",
                      owner_name="Suma Dueño", owner_email="suma.duenio@nutrientrena-qa.com",
                      owner_password="Centro123!").json()["data"]
    client.put(f"/api/admin/organizations/{d['id']}", headers=admin_headers,
               json={"plan_id": pid, "state": "activa"})

    con = client.get("/api/admin/organizations", headers=admin_headers).json()["data"]["totales"]["cuota_contratada"]
    client.put(f"/api/admin/organizations/{d['id']}", headers=admin_headers, json={"state": "suspendida"})
    sin = client.get("/api/admin/organizations", headers=admin_headers).json()["data"]["totales"]["cuota_contratada"]
    assert con - sin == 100, (con, sin)
