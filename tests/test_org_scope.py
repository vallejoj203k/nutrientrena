"""Rutinas y dietas se comparten por organización, no quedan atadas al
usuario exacto que las creó.

Antes de esto, `Routine` nunca rellenaba `organization_id` al crear, y tanto
rutinas como dietas filtraban el listado por `user_id == current_user.id`: ni
dos coaches del mismo equipo compartían su biblioteca, ni lo que creaba el
superadmin llegaba a nadie. Estos tests cubren exactamente ese
comportamiento — compartir dentro de la organización, no filtrar entre
organizaciones distintas, y no dejar que una copia asignada a un cliente se
cuele en la biblioteca de otro coach.
"""
import uuid

from app.database import SessionLocal
from app.models.organization import Organization, OrganizationMember
from app.models.user import User, UserDetail


def _crear_coach(client, admin_headers, email):
    """Da de alta un coach nuevo y devuelve (user_id, user_detail_id, headers).

    El token se firma directamente en vez de pasar por /api/auth/login: ese
    endpoint tiene un límite de 10 peticiones por minuto y estos tests crean
    muchas cuentas.
    """
    from app.core.security import create_access_token

    r = client.post("/api/users", headers=admin_headers, json={
        "name": email.split("@")[0], "email": email,
        "password": "Coach123!", "role_id": 5,
    })
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        detail = db.query(UserDetail).filter(UserDetail.user_id == user.id).first()
        user_id, detail_id = user.id, detail.id
    finally:
        db.close()

    token = create_access_token({"sub": str(user_id)})
    return user_id, detail_id, {"Authorization": f"Bearer {token}"}


def _crear_organizacion(owner_detail_id, name):
    db = SessionLocal()
    try:
        org = Organization(id=str(uuid.uuid4()), name=name, owner_id=owner_detail_id)
        db.add(org)
        db.commit()
        return org.id
    finally:
        db.close()


def _agregar_miembro(org_id, member_detail_id):
    db = SessionLocal()
    try:
        db.add(OrganizationMember(organization_id=org_id, user_detail_id=member_detail_id, permissions={}))
        db.commit()
    finally:
        db.close()


def _crear_cliente(client, headers):
    """Un coach da de alta a su propio cliente (rol 6)."""
    import random
    email = f"cliente{random.randint(0, 10_000_000)}@ejemplo.com"
    r = client.post("/api/users", headers=headers, json={
        "name": "Cliente", "email": email, "password": "Cliente123!", "role_id": 6,
    })
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


# ── Rutinas ───────────────────────────────────────────────────────────────────

def test_rutinas_se_comparten_dentro_de_la_misma_organizacion(client, seed, admin_headers):
    _uid_s, det_s, h_sergio = _crear_coach(client, admin_headers, "sergio.rutinas@nutrientrena-qa.com")
    _uid_a, det_a, h_andres = _crear_coach(client, admin_headers, "andres.rutinas@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_s, "NutriEntrena (rutinas)")
    _agregar_miembro(org_id, det_a)

    r = client.post("/api/routines", headers=h_sergio, json={"name": "Fuerza — Sergio"})
    assert r.status_code == 200, r.text

    r = client.get("/api/routines/findAll", headers=h_andres)
    nombres = [x["name"] for x in r.json()["data"]]
    assert "Fuerza — Sergio" in nombres, nombres


def test_rutinas_no_se_ven_entre_organizaciones_distintas(client, seed, admin_headers):
    _uid_a, det_a, h_org_a = _crear_coach(client, admin_headers, "coach.orga.rutinas@nutrientrena-qa.com")
    _uid_b, det_b, h_org_b = _crear_coach(client, admin_headers, "coach.orgb.rutinas@nutrientrena-qa.com")
    _crear_organizacion(det_a, "Organización A (rutinas)")
    _crear_organizacion(det_b, "Organización B (rutinas)")

    client.post("/api/routines", headers=h_org_a, json={"name": "Solo de la organización A"})
    client.post("/api/routines", headers=h_org_b, json={"name": "Solo de la organización B"})

    nombres_a = [x["name"] for x in client.get("/api/routines/findAll", headers=h_org_a).json()["data"]]
    nombres_b = [x["name"] for x in client.get("/api/routines/findAll", headers=h_org_b).json()["data"]]
    assert "Solo de la organización A" in nombres_a
    assert "Solo de la organización B" not in nombres_a
    assert "Solo de la organización B" in nombres_b
    assert "Solo de la organización A" not in nombres_b


def test_rutina_creada_por_superadmin_es_visible_a_toda_organizacion(client, seed, admin_headers):
    _uid, det, h_coach = _crear_coach(client, admin_headers, "coach.plataforma.rutinas@nutrientrena-qa.com")
    _crear_organizacion(det, "Organización con plantilla de plataforma")

    r = client.post("/api/routines", headers=admin_headers, json={"name": "Plantilla de plataforma — rutina"})
    assert r.status_code == 200, r.text

    nombres = [x["name"] for x in client.get("/api/routines/findAll", headers=h_coach).json()["data"]]
    assert "Plantilla de plataforma — rutina" in nombres


def test_clonar_rutina_de_otra_organizacion_esta_prohibido(client, seed, admin_headers):
    _uid_a, det_a, h_org_a = _crear_coach(client, admin_headers, "coach.orga.clone@nutrientrena-qa.com")
    _uid_b, det_b, h_org_b = _crear_coach(client, admin_headers, "coach.orgb.clone@nutrientrena-qa.com")
    _crear_organizacion(det_a, "Organización A (clone)")
    _crear_organizacion(det_b, "Organización B (clone)")

    r = client.post("/api/routines", headers=h_org_a, json={"name": "Privada de A"})
    routine_id = r.json()["data"]["id"]

    r = client.post("/api/routines/clone", headers=h_org_b, json={"id": routine_id})
    assert r.status_code == 403, r.text


def test_asignar_a_cliente_una_rutina_de_otra_organizacion_esta_prohibido(client, seed, admin_headers):
    _uid_a, det_a, h_org_a = _crear_coach(client, admin_headers, "coach.orga.assign@nutrientrena-qa.com")
    _uid_b, det_b, h_org_b = _crear_coach(client, admin_headers, "coach.orgb.assign@nutrientrena-qa.com")
    _crear_organizacion(det_a, "Organización A (assign)")
    _crear_organizacion(det_b, "Organización B (assign)")

    r = client.post("/api/routines", headers=h_org_a, json={"name": "Privada de A para clonar"})
    routine_id = r.json()["data"]["id"]
    cliente_b = _crear_cliente(client, h_org_b)

    r = client.post(f"/api/routines/{routine_id}/clone-to-client", headers=h_org_b,
                    json={"client_id": cliente_b, "name": "Copia"})
    assert r.status_code == 403, r.text


def test_coach_sin_organizacion_sigue_viendo_solo_lo_suyo(client, seed, coach_headers, admin_headers):
    """El coach sembrado en `seed` no pertenece a ninguna organización: el
    comportamiento de antes (solo lo propio) no debe cambiar para él."""
    _uid, det, h_otro = _crear_coach(client, admin_headers, "otro.sin_org@nutrientrena-qa.com")

    client.post("/api/routines", headers=coach_headers, json={"name": "Del coach sembrado, sin organización"})
    client.post("/api/routines", headers=h_otro, json={"name": "De otro coach, también sin organización"})

    nombres = [x["name"] for x in client.get("/api/routines/findAll", headers=coach_headers).json()["data"]]
    assert "Del coach sembrado, sin organización" in nombres
    assert "De otro coach, también sin organización" not in nombres


# ── Dietas ────────────────────────────────────────────────────────────────────

def test_dietas_se_comparten_dentro_de_la_misma_organizacion(client, seed, admin_headers):
    _uid_s, det_s, h_sergio = _crear_coach(client, admin_headers, "sergio.dietas@nutrientrena-qa.com")
    _uid_a, det_a, h_andres = _crear_coach(client, admin_headers, "andres.dietas@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_s, "NutriEntrena (dietas)")
    _agregar_miembro(org_id, det_a)

    r = client.post("/api/diets", headers=h_sergio, json={"title": "Dieta de Sergio"})
    assert r.status_code == 200, r.text

    titulos = [x["title"] for x in client.get("/api/diets/findAll", headers=h_andres).json()["data"]]
    assert "Dieta de Sergio" in titulos, titulos


def test_dietas_no_se_ven_entre_organizaciones_distintas(client, seed, admin_headers):
    _uid_a, det_a, h_org_a = _crear_coach(client, admin_headers, "coach.orga.dietas@nutrientrena-qa.com")
    _uid_b, det_b, h_org_b = _crear_coach(client, admin_headers, "coach.orgb.dietas@nutrientrena-qa.com")
    _crear_organizacion(det_a, "Organización A (dietas)")
    _crear_organizacion(det_b, "Organización B (dietas)")

    client.post("/api/diets", headers=h_org_a, json={"title": "Solo de la organización A"})
    client.post("/api/diets", headers=h_org_b, json={"title": "Solo de la organización B"})

    titulos_a = [x["title"] for x in client.get("/api/diets/findAll", headers=h_org_a).json()["data"]]
    titulos_b = [x["title"] for x in client.get("/api/diets/findAll", headers=h_org_b).json()["data"]]
    assert "Solo de la organización A" in titulos_a
    assert "Solo de la organización B" not in titulos_a
    assert "Solo de la organización B" in titulos_b
    assert "Solo de la organización A" not in titulos_b


def test_dieta_asignada_a_un_cliente_no_se_cuela_en_la_biblioteca_del_equipo(client, seed, admin_headers):
    """La fila asignada reutiliza la misma tabla con user_id apuntando al
    cliente: si el filtro se equivocara, el plan de un cliente aparecería
    como plantilla reutilizable para cualquier coach del equipo."""
    _uid_s, det_s, h_sergio = _crear_coach(client, admin_headers, "sergio.assign_dieta@nutrientrena-qa.com")
    _uid_a, det_a, h_andres = _crear_coach(client, admin_headers, "andres.assign_dieta@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_s, "NutriEntrena (asignación de dietas)")
    _agregar_miembro(org_id, det_a)

    r = client.post("/api/diets", headers=h_sergio, json={"title": "Plantilla de Sergio"})
    diet_id = r.json()["data"]["id"]
    cliente = _crear_cliente(client, h_sergio)

    r = client.post(f"/api/diets/{diet_id}/assign", headers=h_sergio,
                    json={"client_id": cliente, "title": "Plan de Ana — semana 1"})
    assert r.status_code == 200, r.text

    titulos = [x["title"] for x in client.get("/api/diets/findAll", headers=h_andres).json()["data"]]
    assert "Plantilla de Sergio" in titulos
    assert "Plan de Ana — semana 1" not in titulos, (
        "una dieta ya asignada a un cliente no debe verse como plantilla del equipo"
    )


def test_asignar_a_cliente_una_dieta_de_otra_organizacion_esta_prohibido(client, seed, admin_headers):
    _uid_a, det_a, h_org_a = _crear_coach(client, admin_headers, "coach.orga.assign_dieta@nutrientrena-qa.com")
    _uid_b, det_b, h_org_b = _crear_coach(client, admin_headers, "coach.orgb.assign_dieta@nutrientrena-qa.com")
    _crear_organizacion(det_a, "Organización A (asignar dieta)")
    _crear_organizacion(det_b, "Organización B (asignar dieta)")

    r = client.post("/api/diets", headers=h_org_a, json={"title": "Privada de A"})
    diet_id = r.json()["data"]["id"]
    cliente_b = _crear_cliente(client, h_org_b)

    r = client.post(f"/api/diets/{diet_id}/assign", headers=h_org_b,
                    json={"client_id": cliente_b, "title": "Copia"})
    assert r.status_code == 403, r.text


def test_superadmin_sigue_viendo_toda_la_biblioteca(client, seed, admin_headers):
    """SUPERADMIN no tiene organización propia: debe ver TODO, como antes de
    este cambio y de forma consistente con como ya funciona en aliments.py."""
    _uid, det, h_coach = _crear_coach(client, admin_headers, "coach.para_superadmin@nutrientrena-qa.com")
    _crear_organizacion(det, "Organización visible para superadmin")

    client.post("/api/diets", headers=h_coach, json={"title": "Dieta que el superadmin debe poder ver"})

    titulos = [x["title"] for x in client.get("/api/diets/findAll", headers=admin_headers).json()["data"]]
    assert "Dieta que el superadmin debe poder ver" in titulos


# ── Editar / eliminar: propietario, equipo, cliente asignado ─────────────────
# Antes, `PUT .../update` y `DELETE ...` no comprobaban nada: cualquier coach
# podía tocar cualquier rutina o dieta por id. Estos tests cubren las tres
# reglas nuevas y, sobre todo, que ninguna rompa el caso de siempre: un coach
# editando su propio contenido o el plan ya asignado a su propio cliente.

def test_coach_sin_organizacion_puede_editar_su_propia_rutina(client, seed, admin_headers):
    """Este es justo el caso que casi se rompe: sin organización, organization_id
    queda NULL, y una regla mal escrita podría confundirlo con 'contenido de
    plataforma' y bloquear al propio autor."""
    _uid, _det, h = _crear_coach(client, admin_headers, "coach.edita_lo_suyo@nutrientrena-qa.com")
    r = client.post("/api/routines", headers=h, json={"name": "Mía, sin organización"})
    routine_id = r.json()["data"]["id"]

    r = client.put(f"/api/routines/{routine_id}/update", headers=h, json={"name": "Mía, editada"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["name"] == "Mía, editada"


def test_coach_de_la_misma_organizacion_puede_editar_rutina_del_equipo(client, seed, admin_headers):
    _uid_s, det_s, h_sergio = _crear_coach(client, admin_headers, "sergio.editar_equipo@nutrientrena-qa.com")
    _uid_a, det_a, h_andres = _crear_coach(client, admin_headers, "andres.editar_equipo@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_s, "NutriEntrena (editar en equipo)")
    _agregar_miembro(org_id, det_a)

    r = client.post("/api/routines", headers=h_sergio, json={"name": "De Sergio"})
    routine_id = r.json()["data"]["id"]

    r = client.put(f"/api/routines/{routine_id}/update", headers=h_andres, json={"name": "Editada por Andrés"})
    assert r.status_code == 200, r.text


def test_coach_de_otra_organizacion_no_puede_editar_ni_eliminar(client, seed, admin_headers):
    _uid_a, det_a, h_org_a = _crear_coach(client, admin_headers, "coach.orga.editar@nutrientrena-qa.com")
    _uid_b, det_b, h_org_b = _crear_coach(client, admin_headers, "coach.orgb.editar@nutrientrena-qa.com")
    _crear_organizacion(det_a, "Organización A (editar)")
    _crear_organizacion(det_b, "Organización B (editar)")

    r = client.post("/api/routines", headers=h_org_a, json={"name": "Privada de A"})
    routine_id = r.json()["data"]["id"]

    r = client.get(f"/api/routines/{routine_id}/edit", headers=h_org_b)
    assert r.status_code == 403, r.text
    r = client.put(f"/api/routines/{routine_id}/update", headers=h_org_b, json={"name": "Hackeada"})
    assert r.status_code == 403, r.text
    r = client.delete(f"/api/routines/{routine_id}", headers=h_org_b)
    assert r.status_code == 403, r.text


def test_coach_puede_editar_la_dieta_ya_asignada_a_su_propio_cliente(client, seed, admin_headers):
    """El caso que más se usa en la app: el coach edita el plan que él mismo
    le asignó a su cliente. No debe verse afectado por nada de esto."""
    _uid, _det, h = _crear_coach(client, admin_headers, "coach.edita_cliente@nutrientrena-qa.com")
    r = client.post("/api/diets", headers=h, json={"title": "Plantilla"})
    diet_id = r.json()["data"]["id"]
    cliente = _crear_cliente(client, h)

    r = client.post(f"/api/diets/{diet_id}/assign", headers=h,
                    json={"client_id": cliente, "title": "Plan de mi cliente"})
    assert r.status_code == 200, r.text
    dieta_asignada_id = r.json()["data"]["id"]

    r = client.put(f"/api/diets/{dieta_asignada_id}/update", headers=h,
                json={"id": dieta_asignada_id, "title": "Plan actualizado"})
    assert r.status_code == 200, r.text


def test_coach_no_puede_editar_dieta_asignada_al_cliente_de_otro_coach(client, seed, admin_headers):
    """El acceso a una dieta ya asignada es por relación coach-cliente, no por
    organización: aunque compartan equipo, Andrés no gestiona a los clientes
    de Sergio."""
    _uid_s, det_s, h_sergio = _crear_coach(client, admin_headers, "sergio.dieta_de_su_cliente@nutrientrena-qa.com")
    _uid_a, det_a, h_andres = _crear_coach(client, admin_headers, "andres.dieta_de_su_cliente@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_s, "NutriEntrena (dieta de cliente ajeno)")
    _agregar_miembro(org_id, det_a)

    r = client.post("/api/diets", headers=h_sergio, json={"title": "Plantilla de Sergio"})
    diet_id = r.json()["data"]["id"]
    cliente_de_sergio = _crear_cliente(client, h_sergio)

    r = client.post(f"/api/diets/{diet_id}/assign", headers=h_sergio,
                    json={"client_id": cliente_de_sergio, "title": "Plan del cliente de Sergio"})
    dieta_asignada_id = r.json()["data"]["id"]

    r = client.put(f"/api/diets/{dieta_asignada_id}/update", headers=h_andres,
                json={"id": dieta_asignada_id, "title": "Intento de Andrés"})
    assert r.status_code == 403, r.text
