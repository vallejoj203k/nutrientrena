"""Soporte: tickets de los coaches y comunicados de la plataforma.

Se prueban las dos mitades a la vez porque tienen que encajar: una bandeja de
entrada sin forma de que entre nada es una pantalla que siempre está vacía, y
un comunicado que no se ve en ninguna parte no es un comunicado.

Lo que más se cuida aquí es el aislamiento. Un ticket lleva dentro lo que a un
coach le está fallando —y a veces el nombre de un cliente—, así que la cuenta
de al lado no puede verlo ni de casualidad.
"""
from app.core.dependencies import SOPORTE
from app.database import SessionLocal
from app.models.organization import Organization

from tests.test_admin_panel import _con_rol
from tests.test_org_scope import _agregar_miembro, _crear_organizacion, _crear_usuario


def _abrir(client, headers, asunto, cuerpo="Detalle", prioridad="media"):
    r = client.post("/api/support/tickets", headers=headers,
                    json={"subject": asunto, "body": cuerpo, "priority": prioridad})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _bandeja(client, headers, estado=None):
    url = "/api/admin/support/tickets" + (f"?estado={estado}" if estado else "")
    r = client.get(url, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _asuntos(datos):
    return [t["subject"] for t in datos["tickets"]]


# ── Abrir un ticket ─────────────────────────────────────────────────────────

def test_un_coach_abre_un_ticket_y_llega_a_la_bandeja_de_alzum(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.tk.abre@nutrientrena-qa.com", role_id=5)
    org_id = _crear_organizacion(det, "Centro que pide ayuda")
    _abrir(client, h, "No me deja asignar una rutina", prioridad="alta")

    datos = _bandeja(client, admin_headers)
    fila = next(t for t in datos["tickets"] if t["subject"] == "No me deja asignar una rutina")
    assert fila["state"] == "abierto"
    assert fila["priority"] == "alta"
    # De qué cuenta viene: sin esto la bandeja no sirve para nada.
    assert fila["organization_id"] == org_id
    assert fila["organization_name"] == "Centro que pide ayuda"


def test_un_coach_sin_organizacion_tambien_puede_pedir_ayuda(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.tk.suelto@nutrientrena-qa.com", role_id=5)
    _abrir(client, h, "Soy nuevo y no encuentro nada")

    fila = next(t for t in _bandeja(client, admin_headers)["tickets"]
                if t["subject"] == "Soy nuevo y no encuentro nada")
    assert fila["organization_id"] is None


def test_el_asunto_es_obligatorio(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.tk.vacio@nutrientrena-qa.com", role_id=5)
    r = client.post("/api/support/tickets", headers=h, json={"subject": "   "})
    assert r.status_code == 400, r.text


# ── Aislamiento entre cuentas ───────────────────────────────────────────────

def test_una_cuenta_no_ve_los_tickets_de_otra(client, seed, admin_headers):
    """Lo más delicado de la sección: dentro de un ticket hay lo que le está
    fallando a alguien, y a veces el nombre de un cliente suyo."""
    _uid_a, det_a, h_a = _crear_usuario(client, admin_headers, "coach.tk.a@nutrientrena-qa.com", role_id=5)
    _uid_b, det_b, h_b = _crear_usuario(client, admin_headers, "coach.tk.b@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det_a, "Centro A tickets")
    _crear_organizacion(det_b, "Centro B tickets")

    tid = _abrir(client, h_a, "Incidencia privada de A")

    mios_b = client.get("/api/support/tickets", headers=h_b).json()["data"]
    assert "Incidencia privada de A" not in [t["subject"] for t in mios_b]

    # Ni de frente por id
    assert client.get(f"/api/support/tickets/{tid}", headers=h_b).status_code == 403
    # Ni respondiendo dentro
    assert client.post(f"/api/support/tickets/{tid}/messages", headers=h_b,
                       json={"body": "Me cuelo"}).status_code == 403


def test_el_equipo_de_la_cuenta_sigue_la_incidencia(client, seed, admin_headers):
    """Si solo lo viera quien lo abrió, un coach de vacaciones dejaría a su
    equipo sin poder seguir la incidencia."""
    _uid_d, det_d, h_d = _crear_usuario(client, admin_headers, "duenio.tk.equipo@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det_d, "Centro con equipo de soporte")
    _uid_c, det_c, h_c = _crear_usuario(client, admin_headers, "coach.tk.equipo@nutrientrena-qa.com", role_id=5)
    _agregar_miembro(org_id, det_c)

    _abrir(client, h_c, "Lo abre el coach del equipo")
    asuntos = [t["subject"] for t in client.get("/api/support/tickets", headers=h_d).json()["data"]]
    assert "Lo abre el coach del equipo" in asuntos


def test_un_coach_no_entra_en_la_bandeja_de_la_plataforma(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.tk.bandeja@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/support/tickets", headers=h).status_code == 403


def test_soporte_de_alzum_si_entra(client, seed, admin_headers):
    _uid, _det, h = _con_rol(client, admin_headers, "soporte.tk@nutrientrena-qa.com", SOPORTE)
    assert client.get("/api/admin/support/tickets", headers=h).status_code == 200


# ── Conversación y estados ──────────────────────────────────────────────────

def test_responder_desde_alzum_pasa_el_ticket_a_en_curso(client, seed, admin_headers):
    """Si hubiera que acordarse de moverlo a mano, la bandeja mentiría a los
    dos días."""
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.tk.responde@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro que recibe respuesta")
    tid = _abrir(client, h, "Pregunta que se responde")

    r = client.post(f"/api/support/tickets/{tid}/messages", headers=admin_headers,
                    json={"body": "Lo estamos mirando."})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["state"] == "en_curso"

    # Y el coach ve la respuesta, marcada como de la plataforma
    hilo = client.get(f"/api/support/tickets/{tid}", headers=h).json()["data"]["mensajes"]
    assert [m["body"] for m in hilo] == ["Lo estamos mirando."]
    assert hilo[0]["de_plataforma"] is True


def test_la_respuesta_del_coach_no_cambia_el_estado(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.tk.insiste@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro que insiste")
    tid = _abrir(client, h, "Sigo con el problema")

    client.post(f"/api/support/tickets/{tid}/messages", headers=h, json={"body": "¿Alguna novedad?"})
    fila = next(t for t in _bandeja(client, admin_headers)["tickets"] if t["id"] == tid)
    assert fila["state"] == "abierto"

    hilo = client.get(f"/api/admin/support/tickets/{tid}", headers=admin_headers).json()["data"]["mensajes"]
    assert hilo[0]["de_plataforma"] is False


def test_marcar_resuelto_y_los_contadores(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.tk.cierra@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro que se cierra")
    tid = _abrir(client, h, "Incidencia que se cierra")

    antes = _bandeja(client, admin_headers)["totales"]
    r = client.put(f"/api/admin/support/tickets/{tid}/state", headers=admin_headers,
                   json={"state": "resuelto"})
    assert r.status_code == 200, r.text

    despues = _bandeja(client, admin_headers)["totales"]
    assert despues["resueltos"] == antes["resueltos"] + 1
    assert despues["abiertos"] == antes["abiertos"] - 1

    # Y se puede filtrar por estado
    assert "Incidencia que se cierra" in _asuntos(_bandeja(client, admin_headers, "resuelto"))
    assert "Incidencia que se cierra" not in _asuntos(_bandeja(client, admin_headers, "abierto"))


def test_un_estado_inventado_se_rechaza(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.tk.estado@nutrientrena-qa.com", role_id=5)
    tid = _abrir(client, h, "Ticket con estado raro")
    r = client.put(f"/api/admin/support/tickets/{tid}/state", headers=admin_headers,
                   json={"state": "archivado"})
    assert r.status_code == 400, r.text


# ── Comunicados ─────────────────────────────────────────────────────────────

def _crear_comunicado(client, headers, title, audience="todos"):
    r = client.post("/api/admin/support/announcements", headers=headers,
                    json={"title": title, "body": "Cuerpo del aviso", "audience": audience})
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _publicar(client, headers, cid, estado="publicado"):
    r = client.put(f"/api/admin/support/announcements/{cid}/state", headers=headers,
                   json={"state": estado})
    assert r.status_code == 200, r.text


def _titulos_para(client, headers):
    r = client.get("/api/support/announcements", headers=headers)
    assert r.status_code == 200, r.text
    return [a["title"] for a in r.json()["data"]]


def test_un_comunicado_nace_en_borrador_y_no_lo_ve_nadie(client, seed, admin_headers):
    """Escribir un aviso a todas las cuentas y que salga solo por darle a
    guardar da demasiado miedo como para usar la pantalla con calma."""
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.com.borrador@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro que no ve borradores")

    d = _crear_comunicado(client, admin_headers, "Aviso todavía sin publicar")
    assert d["state"] == "borrador"
    assert "Aviso todavía sin publicar" not in _titulos_para(client, h)


def test_publicar_lo_hace_visible_y_despublicar_lo_retira(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.com.ve@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro que ve el aviso")

    d = _crear_comunicado(client, admin_headers, "Mantenimiento del domingo")
    _publicar(client, admin_headers, d["id"])
    assert "Mantenimiento del domingo" in _titulos_para(client, h)

    _publicar(client, admin_headers, d["id"], "borrador")
    assert "Mantenimiento del domingo" not in _titulos_para(client, h)


def test_la_audiencia_se_resuelve_al_leer_no_al_publicar(client, seed, admin_headers):
    """Se guarda el criterio, no la lista de destinatarios: una cuenta que pase
    de prueba a activa tiene que empezar a recibir lo que le toca sin que nadie
    recalcule nada."""
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.com.audiencia@nutrientrena-qa.com", role_id=5)
    org_id = _crear_organizacion(det, "Centro que cambia de estado")

    db = SessionLocal()
    try:
        db.query(Organization).filter(Organization.id == org_id).first().state = "prueba"
        db.commit()
    finally:
        db.close()

    d = _crear_comunicado(client, admin_headers, "Solo para cuentas activas", audience="activos")
    _publicar(client, admin_headers, d["id"])
    assert "Solo para cuentas activas" not in _titulos_para(client, h)

    # La cuenta pasa a activa: el mismo comunicado, ya publicado, le alcanza
    db = SessionLocal()
    try:
        db.query(Organization).filter(Organization.id == org_id).first().state = "activa"
        db.commit()
    finally:
        db.close()
    assert "Solo para cuentas activas" in _titulos_para(client, h)


def test_una_audiencia_inventada_se_rechaza(client, seed, admin_headers):
    r = client.post("/api/admin/support/announcements", headers=admin_headers,
                    json={"title": "Aviso raro", "audience": "los-guapos"})
    assert r.status_code == 400, r.text


def test_un_coach_no_escribe_comunicados(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.com.escribe@nutrientrena-qa.com", role_id=5)
    assert client.post("/api/admin/support/announcements", headers=h,
                       json={"title": "Aviso del coach"}).status_code == 403
    assert client.get("/api/admin/support/announcements", headers=h).status_code == 403


def test_editar_y_eliminar_un_comunicado(client, seed, admin_headers):
    d = _crear_comunicado(client, admin_headers, "Aviso con erratas")
    r = client.put(f"/api/admin/support/announcements/{d['id']}", headers=admin_headers,
                   json={"title": "Aviso corregido", "body": "Ya está bien", "audience": "prueba"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["title"] == "Aviso corregido"
    assert r.json()["data"]["audience"] == "prueba"

    assert client.delete(f"/api/admin/support/announcements/{d['id']}",
                         headers=admin_headers).status_code == 200
    titulos = [a["title"] for a in
               client.get("/api/admin/support/announcements", headers=admin_headers).json()["data"]]
    assert "Aviso corregido" not in titulos


def test_republicar_no_lo_cuela_arriba_del_todo(client, seed, admin_headers):
    """Despublicar conserva la fecha original."""
    d = _crear_comunicado(client, admin_headers, "Aviso que va y viene")
    _publicar(client, admin_headers, d["id"])
    fecha = next(a["published_at"] for a in
                 client.get("/api/admin/support/announcements", headers=admin_headers).json()["data"]
                 if a["id"] == d["id"])

    _publicar(client, admin_headers, d["id"], "borrador")
    _publicar(client, admin_headers, d["id"])
    fecha2 = next(a["published_at"] for a in
                  client.get("/api/admin/support/announcements", headers=admin_headers).json()["data"]
                  if a["id"] == d["id"])
    assert fecha2 == fecha
