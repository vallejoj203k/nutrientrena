"""Fase 5a: el catálogo de ejercicios respeta la jerarquía de organización.

Antes de esta fase `Training` era una tabla plana de toda la plataforma:
cualquier coach podía editar o borrar el ejercicio de cualquier otro, de
cualquier organización, con solo saber el id. Y como el DELETE desengancha el
ejercicio de `routine_day_details`, borrar uno ajeno rompía las rutinas de otra
organización.

Reglas que se prueban aquí:
- organization_id NULL = catálogo maestro, visible para todos.
- Lo creado dentro de una organización es privado de esa organización.
- Su autor siempre puede editar lo suyo (incluso sin organización).
- Superadmin sigue pudiendo con todo.
"""
from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL
from app.database import SessionLocal
from app.models.training import Training
from app.seeds.roles import seed_roles

from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _crear_ejercicio(client, headers, name):
    r = client.post("/api/trainings", headers=headers, json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _crear_editor(client, admin_headers, email):
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()
    return _crear_usuario(client, admin_headers, email, role_id=EDITOR_CONTENIDO_GLOBAL)


def _ejercicio_de_plataforma(name):
    """Un ejercicio del catálogo maestro, como los que ya existen en producción."""
    db = SessionLocal()
    try:
        obj = Training(name=name, state=1)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj.id
    finally:
        db.close()


# ── Creación ────────────────────────────────────────────────────────────────

def test_el_ejercicio_creado_en_una_organizacion_queda_privado(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.ej.privado@nutrientrena-qa.com", role_id=5)
    org_id = _crear_organizacion(det, "Organización con ejercicios propios")
    tid = _crear_ejercicio(client, h, "Ejercicio privado")

    db = SessionLocal()
    try:
        assert db.get(Training, tid).organization_id == org_id
    finally:
        db.close()


def test_el_superadmin_crea_catalogo_maestro(client, seed, admin_headers):
    """Sin organización propia, lo que crea es de la plataforma (NULL)."""
    tid = _crear_ejercicio(client, admin_headers, "Ejercicio de plataforma")
    db = SessionLocal()
    try:
        assert db.get(Training, tid).organization_id is None
    finally:
        db.close()


# ── Visibilidad ─────────────────────────────────────────────────────────────

def test_una_organizacion_no_ve_los_ejercicios_de_otra(client, seed, admin_headers):
    _uid_a, det_a, h_a = _crear_usuario(client, admin_headers, "coach.ej.orga@nutrientrena-qa.com", role_id=5)
    _uid_b, det_b, h_b = _crear_usuario(client, admin_headers, "coach.ej.orgb@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det_a, "Organización A (ejercicios)")
    _crear_organizacion(det_b, "Organización B (ejercicios)")

    tid_a = _crear_ejercicio(client, h_a, "Solo de A")

    nombres = [i["name"] for i in client.get("/api/trainings/findAll", headers=h_b).json()["data"]]
    assert "Solo de A" not in nombres

    # Ni de frente por id
    r = client.get(f"/api/trainings/{tid_a}/edit", headers=h_b)
    assert r.status_code == 403, r.text

    # Su propia organización sí lo ve
    nombres_a = [i["name"] for i in client.get("/api/trainings/findAll", headers=h_a).json()["data"]]
    assert "Solo de A" in nombres_a


def test_el_catalogo_maestro_lo_ven_todas_las_organizaciones(client, seed, admin_headers):
    """Lo que ya existía sigue siendo compartido: es el punto de la base común."""
    tid = _ejercicio_de_plataforma("Sentadilla del catálogo")
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.ve.catalogo@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Organización que usa el catálogo")

    nombres = [i["name"] for i in client.get("/api/trainings/findAll", headers=h).json()["data"]]
    assert "Sentadilla del catálogo" in nombres

    r = client.get(f"/api/trainings/{tid}/edit", headers=h)
    assert r.status_code == 200, r.text


# ── Edición y borrado ───────────────────────────────────────────────────────

def test_no_puede_editar_ni_borrar_el_ejercicio_de_otra_organizacion(client, seed, admin_headers):
    _uid_a, det_a, h_a = _crear_usuario(client, admin_headers, "coach.ej.edita.a@nutrientrena-qa.com", role_id=5)
    _uid_b, det_b, h_b = _crear_usuario(client, admin_headers, "coach.ej.edita.b@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det_a, "Organización A (edición)")
    _crear_organizacion(det_b, "Organización B (edición)")

    tid = _crear_ejercicio(client, h_a, "Ejercicio de A")

    assert client.put(f"/api/trainings/{tid}/update", headers=h_b, json={"name": "Robado"}).status_code == 403
    assert client.delete(f"/api/trainings/{tid}", headers=h_b).status_code == 403

    # A sí puede con el suyo
    assert client.put(f"/api/trainings/{tid}/update", headers=h_a, json={"name": "Editado por A"}).status_code == 200


def test_un_coach_no_puede_tocar_el_catalogo_maestro(client, seed, admin_headers):
    """Antes cualquier coach podía romper la base compartida de todos."""
    tid = _ejercicio_de_plataforma("Press banca del catálogo")
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.no.toca.catalogo@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Organización que no manda en el catálogo")

    assert client.put(f"/api/trainings/{tid}/update", headers=h, json={"name": "Cambiado"}).status_code == 403
    assert client.delete(f"/api/trainings/{tid}", headers=h).status_code == 403


def test_un_coach_sin_organizacion_puede_editar_su_propio_ejercicio(client, seed, admin_headers):
    """Su ejercicio nace con organization_id NULL; sin la regla de "el autor
    primero", la regla del catálogo maestro le bloquearía lo suyo."""
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.sin.org.ej@nutrientrena-qa.com", role_id=5)
    tid = _crear_ejercicio(client, h, "Ejercicio de coach suelto")

    r = client.put(f"/api/trainings/{tid}/update", headers=h, json={"name": "Corregido por su autor"})
    assert r.status_code == 200, r.text
    assert client.delete(f"/api/trainings/{tid}", headers=h).status_code == 200


def test_el_editor_de_contenido_global_sigue_mandando_en_el_catalogo(client, seed, admin_headers):
    """Regresión de la Fase 4: su trabajo es justo el catálogo maestro."""
    tid = _ejercicio_de_plataforma("Peso muerto del catálogo")
    _uid, _det, h = _crear_editor(client, admin_headers, "editor.ej.catalogo@nutrientrena-qa.com")

    r = client.put(f"/api/trainings/{tid}/update", headers=h, json={"name": "Peso muerto (corregido)"})
    assert r.status_code == 200, r.text


def test_superadmin_sigue_pudiendo_con_cualquier_ejercicio(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.ej.superadmin@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Organización que revisa el superadmin")
    tid = _crear_ejercicio(client, h, "Ejercicio revisado por superadmin")

    r = client.put(f"/api/trainings/{tid}/update", headers=admin_headers, json={"name": "Revisado"})
    assert r.status_code == 200, r.text
    assert client.delete(f"/api/trainings/{tid}", headers=admin_headers).status_code == 200


# ── Asignación ──────────────────────────────────────────────────────────────

def test_no_puede_asignar_un_ejercicio_de_otra_organizacion(client, seed, admin_headers):
    """Asignar es otra vía de acceso: sin comprobarlo, el bloqueo al editar
    no serviría de mucho."""
    _uid_a, det_a, h_a = _crear_usuario(client, admin_headers, "coach.ej.asigna.a@nutrientrena-qa.com", role_id=5)
    uid_b, det_b, h_b = _crear_usuario(client, admin_headers, "coach.ej.asigna.b@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det_a, "Organización A (asignar)")
    _crear_organizacion(det_b, "Organización B (asignar)")

    tid = _crear_ejercicio(client, h_a, "Ejercicio asignable de A")

    r = client.post("/api/trainings/assign", headers=h_b, json={"user_id": uid_b, "training_ids": [tid]})
    assert r.status_code == 403, r.text


def test_puede_asignar_del_catalogo_maestro_y_de_lo_suyo(client, seed, admin_headers):
    tid_plataforma = _ejercicio_de_plataforma("Remo del catálogo")
    uid, det, h = _crear_usuario(client, admin_headers, "coach.ej.asigna.ok@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Organización que asigna bien")
    tid_propio = _crear_ejercicio(client, h, "Ejercicio propio asignable")

    r = client.post("/api/trainings/assign", headers=h, json={
        "user_id": uid, "training_ids": [tid_plataforma, tid_propio]})
    assert r.status_code == 200, r.text
