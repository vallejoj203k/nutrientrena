"""Sección "Equipo Alzum": quién trabaja dentro de la plataforma.

Tres roles internos hoy: super-admin, editor de contenido y soporte.

Lo que más se cuida aquí no es dar de alta gente, es NO poder quedarse fuera.
Quitarle el super-admin al único que hay, o sacarlo del equipo, deja la
plataforma sin nadie que pueda entrar al panel — y eso no se arregla desde la
propia aplicación, hay que ir a la base de datos a mano.
"""
from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL, SOPORTE, SUPERADMIN
from app.database import SessionLocal
from app.models.user import RoleUser, User

from tests.test_admin_panel import _con_rol
from tests.test_org_scope import _crear_usuario


def _equipo(client, headers):
    r = client.get("/api/admin/team", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _miembro(datos, email):
    return next((m for m in datos["miembros"] if m["email"] == email), None)


def _invitar(client, headers, nombre, email, role_id=SOPORTE, clave="Equipo123!"):
    return client.post("/api/admin/team", headers=headers,
                       json={"name": nombre, "email": email, "role_id": role_id, "password": clave})


def _otro_superadmin(client, admin_headers, email="segundo.super@nutrientrena-qa.com"):
    """Un segundo super-admin, para poder probar lo que el último no puede."""
    r = _invitar(client, admin_headers, "Segundo Super", email, role_id=SUPERADMIN)
    assert r.status_code == 200, r.text
    return r.json()["data"]["user_id"]


# ── Quién entra ─────────────────────────────────────────────────────────────

def test_solo_el_superadmin_gestiona_el_equipo(client, seed, admin_headers):
    assert client.get("/api/admin/team", headers=admin_headers).status_code == 200

    # Soporte entra al panel, pero no a esta sección
    _uid, _det, h = _con_rol(client, admin_headers, "soporte.eq@nutrientrena-qa.com", SOPORTE)
    assert client.get("/api/admin/team", headers=h).status_code == 403

    _uid2, _det2, h2 = _crear_usuario(client, admin_headers, "coach.eq@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/team", headers=h2).status_code == 403


def test_se_sirven_los_tres_roles_con_su_descripcion(client, seed, admin_headers):
    """La descripción viene del backend para que lo que dice la tarjeta y lo
    que la API deja hacer no se separen con el tiempo."""
    roles = _equipo(client, admin_headers)["roles"]
    assert [r["role_id"] for r in roles] == [SUPERADMIN, EDITOR_CONTENIDO_GLOBAL, SOPORTE]
    assert all(r["descripcion"] and r["nombre"] for r in roles)
    assert all("miembros" in r for r in roles)


# ── Invitar ─────────────────────────────────────────────────────────────────

def test_invitar_a_alguien_nuevo(client, seed, admin_headers):
    r = _invitar(client, admin_headers, "Lucía Prats", "lucia.eq@nutrientrena-qa.com",
                 role_id=EDITOR_CONTENIDO_GLOBAL)
    assert r.status_code == 200, r.text

    m = _miembro(_equipo(client, admin_headers), "lucia.eq@nutrientrena-qa.com")
    assert m is not None
    assert m["role_id"] == EDITOR_CONTENIDO_GLOBAL
    # No ha entrado nunca: está invitada, no activa
    assert m["state"] == "invitado" and m["last_login_at"] is None

    # Y el rol funciona de verdad, no es solo una etiqueta
    lg = client.post("/api/auth/login", json={"email": "lucia.eq@nutrientrena-qa.com",
                                              "password": "Equipo123!"})
    assert lg.status_code == 200, lg.text
    h = {"Authorization": f"Bearer {lg.json()['data']['token']}"}
    secciones = [s["id"] for s in client.get("/api/admin/me", headers=h).json()["data"]["secciones"]]
    assert secciones == ["contenido"], secciones


def test_entrar_lo_pasa_de_invitado_a_activo(client, seed, admin_headers):
    """"Invitado" y "activo" tienen que significar algo: enseñar como activo a
    quien ni siquiera ha abierto el correo hace creer que ya tiene acceso
    funcionando."""
    correo = "marc.eq@nutrientrena-qa.com"
    _invitar(client, admin_headers, "Marc Ibáñez", correo)
    assert _miembro(_equipo(client, admin_headers), correo)["state"] == "invitado"

    client.post("/api/auth/login", json={"email": correo, "password": "Equipo123!"})

    m = _miembro(_equipo(client, admin_headers), correo)
    assert m["state"] == "activo"
    assert m["last_login_at"] is not None


def test_a_un_coach_que_ya_existe_se_le_anade_el_rol(client, seed, admin_headers):
    """Negarse obligaría a crearle una segunda cuenta con otro correo, que es
    peor: acabaría con dos identidades y el trabajo repartido entre las dos."""
    uid, _det, _h = _crear_usuario(client, admin_headers, "coach.tambien@nutrientrena-qa.com", role_id=5)

    r = _invitar(client, admin_headers, "Coach También", "coach.tambien@nutrientrena-qa.com",
                 role_id=SOPORTE)
    assert r.status_code == 200, r.text

    m = _miembro(_equipo(client, admin_headers), "coach.tambien@nutrientrena-qa.com")
    assert m is not None and m["role_id"] == SOPORTE

    # Sigue siendo coach: no se le ha quitado nada
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == "coach.tambien@nutrientrena-qa.com").first()
        roles = {f.role_id for f in db.query(RoleUser).filter(RoleUser.user_id == u.id).all()}
    finally:
        db.close()
    assert {5, SOPORTE} <= roles, roles


def test_no_se_invita_dos_veces_a_la_misma_persona(client, seed, admin_headers):
    _invitar(client, admin_headers, "Nerea Gil", "nerea.eq@nutrientrena-qa.com")
    r = _invitar(client, admin_headers, "Nerea Gil", "nerea.eq@nutrientrena-qa.com")
    assert r.status_code == 400, r.text


def test_no_se_puede_invitar_con_un_rol_que_no_es_del_equipo(client, seed, admin_headers):
    """Un coach o un cliente no son roles internos. Sin esta comprobación, el
    panel sería una forma de repartir cualquier rol de la plataforma."""
    for rol in (2, 5, 6):
        r = _invitar(client, admin_headers, "Colado", f"colado{rol}@nutrientrena-qa.com", role_id=rol)
        assert r.status_code == 400, (rol, r.text)


def test_hacen_falta_nombre_correo_y_una_clave_decente(client, seed, admin_headers):
    assert _invitar(client, admin_headers, "  ", "sin.nombre@nutrientrena-qa.com").status_code == 400
    assert client.post("/api/admin/team", headers=admin_headers, json={
        "name": "Sin correo", "email": "  ", "role_id": SOPORTE, "password": "Equipo123!"}).status_code == 400
    assert _invitar(client, admin_headers, "Clave Corta", "clave.corta@nutrientrena-qa.com",
                    clave="123").status_code == 400


# ── Cambiar de rol ──────────────────────────────────────────────────────────

def test_cambiar_el_rol_cambia_lo_que_ve_en_el_panel(client, seed, admin_headers):
    correo = "cambia.rol@nutrientrena-qa.com"
    uid = _invitar(client, admin_headers, "Cambia Rol", correo, role_id=SOPORTE).json()["data"]["user_id"]

    r = client.put(f"/api/admin/team/{uid}/role", headers=admin_headers,
                   json={"role_id": EDITOR_CONTENIDO_GLOBAL})
    assert r.status_code == 200, r.text

    lg = client.post("/api/auth/login", json={"email": correo, "password": "Equipo123!"})
    h = {"Authorization": f"Bearer {lg.json()['data']['token']}"}
    secciones = [s["id"] for s in client.get("/api/admin/me", headers=h).json()["data"]["secciones"]]
    assert secciones == ["contenido"], secciones

    # Y el rol viejo se ha ido: no se acumulan
    assert _miembro(_equipo(client, admin_headers), correo)["role_id"] == EDITOR_CONTENIDO_GLOBAL


def test_no_se_puede_poner_un_rol_que_no_es_del_equipo(client, seed, admin_headers):
    uid = _invitar(client, admin_headers, "Rol Raro", "rol.raro@nutrientrena-qa.com").json()["data"]["user_id"]
    assert client.put(f"/api/admin/team/{uid}/role", headers=admin_headers,
                      json={"role_id": 5}).status_code == 400


def test_cambiar_el_rol_de_quien_no_esta_en_el_equipo_da_404(client, seed, admin_headers):
    uid, _det, _h = _crear_usuario(client, admin_headers, "fuera.equipo@nutrientrena-qa.com", role_id=5)
    assert client.put(f"/api/admin/team/{uid}/role", headers=admin_headers,
                      json={"role_id": SOPORTE}).status_code == 404


# ── No quedarse fuera ───────────────────────────────────────────────────────

def test_al_unico_superadmin_no_se_le_quita_el_rol(client, seed, admin_headers):
    """Lo importante de toda la sección. Un clic y la plataforma se queda sin
    nadie que pueda entrar al panel, y eso no se arregla desde la aplicación."""
    db = SessionLocal()
    try:
        supers = [f.user_id for f in db.query(RoleUser).filter(RoleUser.role_id == SUPERADMIN).all()]
    finally:
        db.close()
    assert len(supers) == 1, supers

    r = client.put(f"/api/admin/team/{supers[0]}/role", headers=admin_headers,
                   json={"role_id": SOPORTE})
    assert r.status_code == 400, r.text
    assert "único" in r.json()["message"].lower()

    # Y sigue siendo super-admin
    db = SessionLocal()
    try:
        assert db.query(RoleUser).filter(RoleUser.role_id == SUPERADMIN).count() == 1
    finally:
        db.close()


def test_al_unico_superadmin_tampoco_se_le_saca_del_equipo(client, seed, admin_headers):
    db = SessionLocal()
    try:
        uid = db.query(RoleUser).filter(RoleUser.role_id == SUPERADMIN).first().user_id
    finally:
        db.close()
    r = client.delete(f"/api/admin/team/{uid}", headers=admin_headers)
    assert r.status_code == 400, r.text


def test_con_dos_superadmin_ya_se_puede_degradar_a_uno(client, seed, admin_headers):
    """La protección es "el último", no "los super-admin son intocables"."""
    otro = _otro_superadmin(client, admin_headers, "degradable@nutrientrena-qa.com")
    r = client.put(f"/api/admin/team/{otro}/role", headers=admin_headers,
                   json={"role_id": SOPORTE})
    assert r.status_code == 200, r.text
    assert _miembro(_equipo(client, admin_headers), "degradable@nutrientrena-qa.com")["role_id"] == SOPORTE


def test_nadie_se_saca_a_si_mismo_del_equipo(client, seed, admin_headers):
    """Aunque haya otro super-admin: es un clic del que no se vuelve y no
    resuelve ningún problema real."""
    _otro_superadmin(client, admin_headers, "otro.para.salir@nutrientrena-qa.com")

    db = SessionLocal()
    try:
        yo = db.query(User).filter(User.email == "admin@test.com").first().id
    finally:
        db.close()
    r = client.delete(f"/api/admin/team/{yo}", headers=admin_headers)
    assert r.status_code == 400, r.text
    assert "ti mismo" in r.json()["message"].lower()


# ── Sacar del equipo ────────────────────────────────────────────────────────

def test_sacar_del_equipo_quita_el_acceso_pero_no_borra_la_cuenta(client, seed, admin_headers):
    """Puede ser también coach con sus clientes: borrar el usuario se llevaría
    por delante su trabajo."""
    correo = "coach.y.soporte@nutrientrena-qa.com"
    uid, _det, _h = _crear_usuario(client, admin_headers, correo, role_id=5)
    _invitar(client, admin_headers, "Coach y Soporte", correo, role_id=SOPORTE)

    r = client.delete(f"/api/admin/team/{uid}", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _miembro(_equipo(client, admin_headers), correo) is None

    # La cuenta sigue, y sigue siendo coach
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == correo).first()
        assert u is not None
        roles = {f.role_id for f in db.query(RoleUser).filter(RoleUser.user_id == u.id).all()}
    finally:
        db.close()
    assert roles == {5}, roles

    # Y ya no entra al panel
    lg = client.post("/api/auth/login", json={"email": correo, "password": "Password123!"})
    if lg.status_code == 200:
        h = {"Authorization": f"Bearer {lg.json()['data']['token']}"}
        assert client.get("/api/admin/me", headers=h).status_code == 403


def test_sacar_a_quien_no_esta_da_404(client, seed, admin_headers):
    uid, _det, _h = _crear_usuario(client, admin_headers, "nunca.estuvo@nutrientrena-qa.com", role_id=5)
    assert client.delete(f"/api/admin/team/{uid}", headers=admin_headers).status_code == 404


def test_quien_tiene_dos_roles_internos_sale_una_vez_con_el_mas_alto(client, seed, admin_headers):
    """Si saliera dos veces, la pantalla enseñaría a la misma persona con dos
    permisos distintos y no se sabría cuál manda."""
    correo = "doble.rol@nutrientrena-qa.com"
    uid = _invitar(client, admin_headers, "Doble Rol", correo, role_id=SOPORTE).json()["data"]["user_id"]
    db = SessionLocal()
    try:
        db.add(RoleUser(role_id=EDITOR_CONTENIDO_GLOBAL, user_id=uid))
        db.commit()
    finally:
        db.close()

    filas = [m for m in _equipo(client, admin_headers)["miembros"] if m["email"] == correo]
    assert len(filas) == 1, filas
    assert filas[0]["role_id"] == EDITOR_CONTENIDO_GLOBAL, filas


def test_me_reconozco_a_mi_mismo_en_la_lista(client, seed, admin_headers):
    """La pantalla marca "(tú)" y esconde el botón de borrarte."""
    m = _miembro(_equipo(client, admin_headers), "admin@test.com")
    assert m is not None and m["soy_yo"] is True
    assert all(o["soy_yo"] is False for o in _equipo(client, admin_headers)["miembros"]
               if o["email"] != "admin@test.com")
