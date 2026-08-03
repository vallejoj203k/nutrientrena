"""Fase 3: `TeamMember` (la tabla real detrás de la pantalla "Coaches") pasa
a respetar la jerarquía de organizaciones, y `get_org_context` reconoce a
alguien como miembro de una organización tanto si se le dio de alta desde
"Coaches" (TeamMember) como desde "Mi Organización" (OrganizationMember) —
dos pantallas que hasta ahora no se hablaban entre sí.

Antes de esto, TeamMember no tenía organization_id: era una lista plana de
toda la plataforma. Con la Fase 2 (un ADMIN dueño de organización ya actúa
dentro de ella) eso se volvía un hueco real — cualquier ADMIN veía y podía
editar el equipo de cualquier otra organización. Y como "Coaches" es la
pantalla que de verdad se usa para añadir gente, un coach dado de alta ahí
nunca quedaba reconocido por get_org_context, así que nada de lo compartido
por organización (rutinas, dietas) le llegaba — aunque su jefe sí tuviera
una organización real.
"""
from app.core.dependencies import get_org_context
from app.database import SessionLocal
from app.models.user import User

from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _contexto_de(user_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return get_org_context(current_user=user, db=db)
    finally:
        db.close()


def _agregar_al_equipo(client, headers, user_detail_id, **extra):
    r = client.post("/api/team", headers=headers, json={"user_detail_id": user_detail_id, **extra})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def test_get_org_context_reconoce_a_quien_se_agrego_desde_coaches(client, seed, admin_headers):
    """El caso central de la Fase 3: alguien añadido por "Coaches" (TeamMember)
    queda reconocido como miembro de la organización de quien lo añadió."""
    uid_admin, det_admin, h_admin = _crear_usuario(client, admin_headers, "jefe.equipo@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det_admin, "NutriEntrena (equipo)")

    uid_coach, det_coach, _h_coach = _crear_usuario(client, admin_headers, "sergio.equipo@nutrientrena-qa.com", role_id=5)
    _agregar_al_equipo(client, h_admin, det_coach)

    ctx = _contexto_de(uid_coach)
    assert ctx.org_id == org_id
    assert ctx.is_owner is False


def test_equipo_se_filtra_por_organizacion(client, seed, admin_headers):
    uid_a, det_a, h_org_a = _crear_usuario(client, admin_headers, "admin.orga.equipo@nutrientrena-qa.com", role_id=2)
    uid_b, det_b, h_org_b = _crear_usuario(client, admin_headers, "admin.orgb.equipo@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det_a, "Organización A (equipo)")
    _crear_organizacion(det_b, "Organización B (equipo)")

    r = client.post("/api/team", headers=h_org_a, json={"member_name": "Solo en A"})
    assert r.status_code == 200, r.text
    r = client.post("/api/team", headers=h_org_b, json={"member_name": "Solo en B"})
    assert r.status_code == 200, r.text

    nombres_a = [m["member_name"] for m in client.get("/api/team", headers=h_org_a).json()["data"]]
    nombres_b = [m["member_name"] for m in client.get("/api/team", headers=h_org_b).json()["data"]]
    assert "Solo en A" in nombres_a
    assert "Solo en B" not in nombres_a
    assert "Solo en B" in nombres_b
    assert "Solo en A" not in nombres_b


def test_admin_no_puede_editar_ni_eliminar_miembro_de_otra_organizacion(client, seed, admin_headers):
    uid_a, det_a, h_org_a = _crear_usuario(client, admin_headers, "admin.orga.editar_equipo@nutrientrena-qa.com", role_id=2)
    uid_b, det_b, h_org_b = _crear_usuario(client, admin_headers, "admin.orgb.editar_equipo@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det_a, "Organización A (editar equipo)")
    _crear_organizacion(det_b, "Organización B (editar equipo)")

    r = client.post("/api/team", headers=h_org_a, json={"member_name": "Miembro de A"})
    member_id = r.json()["data"]["id"]

    r = client.put(f"/api/team/{member_id}", headers=h_org_b, json={"member_name": "Hackeado"})
    assert r.status_code == 403, r.text
    r = client.delete(f"/api/team/{member_id}", headers=h_org_b)
    assert r.status_code == 403, r.text

    # El propio dueño de la organización A sí puede
    r = client.put(f"/api/team/{member_id}", headers=h_org_a, json={"member_name": "Editado por su dueño"})
    assert r.status_code == 200, r.text


def test_superadmin_ve_y_edita_cualquier_miembro(client, seed, admin_headers):
    uid, det, h_admin = _crear_usuario(client, admin_headers, "admin.para_superadmin.equipo@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det, "Organización visible para superadmin")

    r = client.post("/api/team", headers=h_admin, json={"member_name": "Miembro visible para superadmin"})
    member_id = r.json()["data"]["id"]

    nombres = [m["member_name"] for m in client.get("/api/team", headers=admin_headers).json()["data"]]
    assert "Miembro visible para superadmin" in nombres

    r = client.put(f"/api/team/{member_id}", headers=admin_headers, json={"member_name": "Editado por superadmin"})
    assert r.status_code == 200, r.text


def test_coach_agregado_por_coaches_comparte_rutinas_con_su_organizacion(client, seed, admin_headers):
    """La comprobación de punta a punta: sin la Fase 3, un coach añadido desde
    "Coaches" nunca quedaba reconocido por get_org_context, así que aunque su
    jefe tuviera una organización real, nada de lo compartido (Fase 1) le
    llegaba. Con esto, sí."""
    uid_jefe, det_jefe, h_jefe = _crear_usuario(client, admin_headers, "jefe.comparte_rutinas@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det_jefe, "NutriEntrena (comparte rutinas)")

    uid_coach, det_coach, h_coach = _crear_usuario(client, admin_headers, "andres.comparte_rutinas@nutrientrena-qa.com", role_id=5)
    _agregar_al_equipo(client, h_jefe, det_coach)

    r = client.post("/api/routines", headers=h_jefe, json={"name": "Fuerza del jefe"})
    assert r.status_code == 200, r.text

    nombres = [x["name"] for x in client.get("/api/routines/findAll", headers=h_coach).json()["data"]]
    assert "Fuerza del jefe" in nombres, nombres


def test_admin_delegado_ve_solo_su_organizacion_pero_no_puede_editar(client, seed, admin_headers):
    """Un ADMIN que es miembro (no dueño) de la organización de otro: antes de
    este ajuste habría visto TODA la plataforma, porque el filtro de listado
    exigía ser dueño. Ver debe depender de tener organización, no de ser su
    dueño; editar sí sigue exigiendo ser el dueño."""
    from tests.test_org_scope import _agregar_miembro

    uid_dueno, det_dueno, h_dueno = _crear_usuario(client, admin_headers, "dueno.delegado_equipo@nutrientrena-qa.com", role_id=2)
    uid_delegado, det_delegado, h_delegado = _crear_usuario(client, admin_headers, "delegado.equipo@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det_dueno, "Organización con admin delegado (equipo)")
    _agregar_miembro(org_id, det_delegado)

    r = client.post("/api/team", headers=h_dueno, json={"member_name": "De la organización del dueño"})
    member_id = r.json()["data"]["id"]

    uid_ajeno, det_ajeno, h_ajeno = _crear_usuario(client, admin_headers, "ajeno.equipo@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det_ajeno, "Organización totalmente ajena (equipo)")
    client.post("/api/team", headers=h_ajeno, json={"member_name": "De otra organización"})

    nombres = [m["member_name"] for m in client.get("/api/team", headers=h_delegado).json()["data"]]
    assert "De la organización del dueño" in nombres
    assert "De otra organización" not in nombres

    r = client.put(f"/api/team/{member_id}", headers=h_delegado, json={"member_name": "Intento del delegado"})
    assert r.status_code == 403, r.text


# ── El dueño del centro puede ser COACH, no solo ADMIN ─────────────────────
# El gate de rol era (SUPERADMIN, ADMIN), así que un dueño registrado como
# COACH quedaba fuera de su propia pantalla de Equipo. El documento de
# jerarquía dice que el dueño del centro gestiona su equipo, sin decir con qué
# rol está dado de alta.

def test_un_coach_duenio_de_organizacion_gestiona_su_equipo(client, seed, admin_headers):
    uid, det, h = _crear_usuario(client, admin_headers, "coach.duenio.centro@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Gimnasio de un coach dueño")

    # Ve su equipo
    r = client.get("/api/team", headers=h)
    assert r.status_code == 200, r.text

    # Y puede dar de alta personal
    r = client.post("/api/team", headers=h, json={"member_name": "Nuevo coach del centro"})
    assert r.status_code == 200, r.text
    member_id = r.json()["data"]["id"]

    # Lo que crea queda en su organización
    r = client.put(f"/api/team/{member_id}", headers=h, json={"member_name": "Renombrado"})
    assert r.status_code == 200, r.text


def test_un_coach_del_equipo_sigue_sin_ver_ni_tocar_el_equipo(client, seed, admin_headers):
    """Nivel 3: gestiona sus clientes y nada más. Abrir el gate a COACH no
    puede convertir a cualquier coach en gestor de personal."""
    uid_d, det_d, h_d = _crear_usuario(client, admin_headers, "duenio.con.empleado@nutrientrena-qa.com", role_id=5)
    org_id = _crear_organizacion(det_d, "Centro con empleado")

    uid_e, det_e, h_e = _crear_usuario(client, admin_headers, "empleado.raso@nutrientrena-qa.com", role_id=5)
    _agregar_al_equipo(client, h_d, det_e)

    assert client.get("/api/team", headers=h_e).status_code == 403
    assert client.post("/api/team", headers=h_e, json={"member_name": "Intento"}).status_code == 403


def test_un_coach_sin_organizacion_no_da_de_alta_personal(client, seed, admin_headers):
    uid, det, h = _crear_usuario(client, admin_headers, "coach.suelto.equipo@nutrientrena-qa.com", role_id=5)
    assert client.post("/api/team", headers=h, json={"member_name": "Intento"}).status_code == 403
