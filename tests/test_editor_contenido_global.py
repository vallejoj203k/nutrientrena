"""Fase 4: el rol "Editor de contenido global" del documento de jerarquía.

Nivel 1 (plataforma), igual que super-admin, pero limitado: puede añadir
alimentos y ejercicios a la base de datos maestra, y NADA más — no gestiona
clientes, no gestiona equipo, no ve ni toca las organizaciones. Es "para el
ayudante que llena la base de datos".

No hay tabla de permisos granular en este backend, así que se modela como un
rol nuevo (id 7) en vez de un permiso dentro de una organización: este rol no
pertenece a ninguna organización por diseño, así que un permiso de
organización no encajaría.
"""
from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL
from app.database import SessionLocal
from app.models.user import RoleUser, User
from app.seeds.roles import seed_roles

from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _crear_editor(client, admin_headers, email):
    """Da de alta un editor de contenido global (rol 7)."""
    db = SessionLocal()
    try:
        seed_roles(db)  # idempotente: se asegura de que exista el rol 7
    finally:
        db.close()
    return _crear_usuario(client, admin_headers, email, role_id=EDITOR_CONTENIDO_GLOBAL)


def test_el_rol_existe_y_se_puede_asignar(client, seed, admin_headers):
    uid, _det, h = _crear_editor(client, admin_headers, "editor.existe@nutrientrena-qa.com")
    db = SessionLocal()
    try:
        assert db.query(RoleUser).filter_by(user_id=uid, role_id=EDITOR_CONTENIDO_GLOBAL).first()
    finally:
        db.close()
    # Y su token de verdad autentica: puede al menos listar el catálogo
    r = client.get("/api/aliments/findAll", headers=h)
    assert r.status_code == 200, r.text


def test_puede_crear_y_editar_alimentos_globales(client, seed, admin_headers):
    _uid, _det, h = _crear_editor(client, admin_headers, "editor.crea_alimentos@nutrientrena-qa.com")

    r = client.post("/api/aliments", headers=h, json={
        "name": "Alimento del editor", "calories": 100, "proteins": 10,
        "carbohydrates": 10, "fats": 2})
    assert r.status_code == 200, r.text
    aliment_id = r.json()["data"]["id"]

    # Sin organización propia: queda global (organization_id NULL), no de
    # ninguna organización en concreto — exactamente su trabajo.
    r = client.get(f"/api/aliments/{aliment_id}/edit", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["organization_id"] is None

    r = client.put(f"/api/aliments/{aliment_id}/update", headers=h, json={"name": "Corregido por el editor"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["name"] == "Corregido por el editor"


def test_antes_de_esta_fase_el_editor_habria_quedado_bloqueado(client, seed, admin_headers):
    """Antes de añadir la excepción, la regla existente ("solo el dueño de
    organización edita contenido de plataforma") habría bloqueado al editor
    para tocar lo único que puede tocar — porque nunca tiene organización
    propia. Se prueba explícitamente para que nadie la quite sin darse cuenta."""
    _uid, _det, h = _crear_editor(client, admin_headers, "editor.no_bloqueado@nutrientrena-qa.com")
    r = client.post("/api/aliments", headers=h, json={
        "name": "Prueba de bloqueo", "calories": 50, "proteins": 5,
        "carbohydrates": 5, "fats": 1})
    aliment_id = r.json()["data"]["id"]

    r = client.put(f"/api/aliments/{aliment_id}/update", headers=h, json={"name": "Sigue pudiendo"})
    assert r.status_code == 200, r.text


def test_puede_crear_ejercicios(client, seed, admin_headers):
    _uid, _det, h = _crear_editor(client, admin_headers, "editor.crea_ejercicios@nutrientrena-qa.com")
    r = client.post("/api/trainings", headers=h, json={"name": "Ejercicio del editor"})
    assert r.status_code == 200, r.text
    training_id = r.json()["data"]["id"]

    r = client.put(f"/api/trainings/{training_id}/update", headers=h, json={"name": "Corregido"})
    assert r.status_code == 200, r.text


def test_no_puede_asignar_ejercicios_a_un_cliente(client, seed, admin_headers):
    """No gestiona clientes: asignar es justamente eso."""
    _uid, _det, h = _crear_editor(client, admin_headers, "editor.no_asigna@nutrientrena-qa.com")
    r = client.post("/api/trainings/assign", headers=h, json={"user_id": 999999, "training_ids": [1]})
    assert r.status_code == 403, r.text


def test_no_puede_crear_clientes(client, seed, admin_headers):
    """No gestiona clientes: dar de alta uno tampoco."""
    _uid, _det, h = _crear_editor(client, admin_headers, "editor.no_crea_clientes@nutrientrena-qa.com")
    r = client.post("/api/users", headers=h, json={
        "name": "Intento", "email": "cliente.del.editor@ejemplo.com",
        "password": "Cliente123!", "role_id": 6})
    assert r.status_code == 403, r.text


def test_no_puede_gestionar_organizaciones_ni_equipo(client, seed, admin_headers):
    """No ve ni gestiona organizaciones ni equipo — nivel 1 limitado, no
    nivel 2."""
    _uid, _det, h = _crear_editor(client, admin_headers, "editor.no_gestiona_org@nutrientrena-qa.com")

    r = client.post("/api/organizations", headers=h, json={"name": "Intento de organización"})
    assert r.status_code == 403, r.text

    r = client.get("/api/team", headers=h)
    assert r.status_code == 403, r.text

    r = client.post("/api/team", headers=h, json={"member_name": "Intento de miembro"})
    assert r.status_code == 403, r.text


def test_no_puede_editar_alimentos_de_una_organizacion_ajena(client, seed, admin_headers):
    """Su trabajo es la base maestra, no el contenido privado de una
    organización — aunque ese contenido esté a la vista en el listado."""
    _uid_admin, det_admin, h_admin = _crear_usuario(client, admin_headers, "admin.duenio_alimento@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det_admin, "Organización con alimento privado")
    r = client.post("/api/aliments", headers=h_admin, json={
        "name": "Alimento privado de la organización", "calories": 80,
        "proteins": 8, "carbohydrates": 8, "fats": 1})
    aliment_id = r.json()["data"]["id"]

    _uid_editor, _det_editor, h_editor = _crear_editor(client, admin_headers, "editor.no_toca_privado@nutrientrena-qa.com")
    r = client.put(f"/api/aliments/{aliment_id}/update", headers=h_editor, json={"name": "Intento del editor"})
    assert r.status_code == 403, r.text


# ── Efecto colateral: cierre del hueco general en aliments.py ───────────────
# Al añadir la excepción del editor de contenido global se destapó que
# aliments.py nunca comprobaba organización al editar — solo bloqueaba el
# contenido de plataforma. Cualquier coach podía editar el alimento privado de
# OTRA organización con solo saber el id. Se cierra con el mismo patrón ya
# probado en rutinas, dietas y equipo.

def test_un_coach_no_puede_editar_alimentos_de_otra_organizacion(client, seed, admin_headers):
    uid_a, det_a, h_org_a = _crear_usuario(client, admin_headers, "coach.orga.alimento@nutrientrena-qa.com", role_id=5)
    uid_b, det_b, h_org_b = _crear_usuario(client, admin_headers, "coach.orgb.alimento@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det_a, "Organización A (alimentos)")
    _crear_organizacion(det_b, "Organización B (alimentos)")

    r = client.post("/api/aliments", headers=h_org_a, json={
        "name": "Alimento privado de A", "calories": 90, "proteins": 9,
        "carbohydrates": 9, "fats": 2})
    aliment_id = r.json()["data"]["id"]

    r = client.put(f"/api/aliments/{aliment_id}/update", headers=h_org_b, json={"name": "Hackeado"})
    assert r.status_code == 403, r.text

    # El propio coach de A sigue pudiendo
    r = client.put(f"/api/aliments/{aliment_id}/update", headers=h_org_a, json={"name": "Editado por A"})
    assert r.status_code == 200, r.text


def test_superadmin_sigue_editando_cualquier_alimento(client, seed, admin_headers):
    uid, det, h = _crear_usuario(client, admin_headers, "coach.para_superadmin.alimento@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Organización cuyo alimento edita superadmin")

    r = client.post("/api/aliments", headers=h, json={
        "name": "Alimento de una organización", "calories": 70, "proteins": 7,
        "carbohydrates": 7, "fats": 1})
    aliment_id = r.json()["data"]["id"]

    r = client.put(f"/api/aliments/{aliment_id}/update", headers=admin_headers, json={"name": "Editado por superadmin"})
    assert r.status_code == 200, r.text


# ── Fase 4.3: el rol se puede dar de alta desde la interfaz ────────────────
# Existía desde la fase 4 con sus permisos y sus pruebas, pero no aparecía en
# ninguna pantalla: había que tocar la base de datos para asignarlo. La pantalla
# de Ajustes lo crea con esta misma llamada.

def test_el_superadmin_puede_dar_de_alta_un_editor(client, seed, admin_headers):
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()

    r = client.post("/api/users", headers=admin_headers, json={
        "name": "Ayudante", "last_name": "De Catálogo",
        "email": "ayudante.catalogo@nutrientrena-qa.com",
        "password": "Catalogo123!", "role_id": EDITOR_CONTENIDO_GLOBAL})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == "ayudante.catalogo@nutrientrena-qa.com").first()
        assert u is not None
        assert db.query(RoleUser).filter_by(user_id=u.id, role_id=EDITOR_CONTENIDO_GLOBAL).first()
    finally:
        db.close()


def test_el_editor_creado_no_queda_atado_a_ninguna_organizacion(client, seed, admin_headers):
    """Es personal de plataforma, no de una organización. Por eso no se crea
    desde la pantalla de Equipo, que ata al miembro a la organización de quien
    lo da de alta."""
    from app.models.team_member import TeamMember
    from app.models.organization import OrganizationMember
    from app.models.user import UserDetail

    _uid, det, _h = _crear_editor(client, admin_headers, "editor.sin.org@nutrientrena-qa.com")

    db = SessionLocal()
    try:
        assert db.query(TeamMember).filter(TeamMember.user_detail_id == det).first() is None
        assert db.query(OrganizationMember).filter(OrganizationMember.user_detail_id == det).first() is None
        assert db.query(UserDetail).filter(UserDetail.id == det).first() is not None
    finally:
        db.close()
