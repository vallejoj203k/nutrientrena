"""«Soy invitado»: reclamar una cuenta desde la pantalla de acceso.

El flujo que pidió el cliente: quien recibe una invitación entra en el login,
pone su correo, el código que le pasaron y crea su contraseña. Sin depender de
que le llegue un correo, y sin que quien invita conozca esa contraseña.

Hace falta el CÓDIGO además del correo, y eso no es burocracia: sin él,
cualquiera que conozca —o adivine— el correo de un invitado podría reclamar la
cuenta antes que su dueño, y aquí se reparten cuentas de super-admin. Casi
todas las pruebas de este fichero son sobre eso.
"""
from datetime import datetime, timedelta

from app.core.dependencies import SOPORTE, SUPERADMIN
from app.database import SessionLocal
from app.models.user import User

from tests.test_org_scope import _crear_usuario


def _invitar(client, admin_headers, nombre, email, role_id=SUPERADMIN):
    """Invita sin contraseña; devuelve (user_id, código en claro)."""
    r = client.post("/api/admin/team", headers=admin_headers,
                    json={"name": nombre, "email": email, "role_id": role_id})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    return d["user_id"], d["codigo_invitacion"]


def _aceptar(client, email, code, password="MiPropia2026!"):
    return client.post("/api/auth/accept-invitation",
                       json={"email": email, "code": code, "password": password})


def _entrar(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _caducar(email, sesion_app):
    """Envejece la invitación.

    Se usa la sesión de la aplicación, no una nueva: en las pruebas todas las
    peticiones comparten una sola sesión, que se queda con el usuario en su
    caché de identidad. Escribiendo desde fuera, la aplicación seguiría viendo
    la fecha vieja y el test mediría lo que no es. En producción cada petición
    trae su propia sesión y esto no pasa.
    """
    u = sesion_app.query(User).filter(User.email == email).first()
    u.invite_expires_at = datetime.utcnow() - timedelta(minutes=1)
    sesion_app.commit()


# ── El camino feliz ─────────────────────────────────────────────────────────

def test_el_invitado_crea_su_contrasena_y_entra(client, seed, admin_headers):
    correo = "invitado.feliz@nutrientrena-qa.com"
    _uid, codigo = _invitar(client, admin_headers, "Invitado Feliz", correo)

    # Antes de reclamarla, la cuenta no se abre
    assert _entrar(client, correo, "MiPropia2026!").status_code == 401

    r = _aceptar(client, correo, codigo)
    assert r.status_code == 200, r.text

    lg = _entrar(client, correo, "MiPropia2026!")
    assert lg.status_code == 200, lg.text

    # Y es super-admin de verdad, no solo una cuenta con contraseña
    h = {"Authorization": f"Bearer {lg.json()['data']['token']}"}
    d = client.get("/api/admin/me", headers=h).json()["data"]
    assert d["es_superadmin"] is True and len(d["secciones"]) == 11


def test_el_codigo_se_devuelve_una_vez_y_no_queda_en_claro(client, seed, admin_headers):
    """Guardarlo en claro para poder volver a enseñarlo convertiría la tabla de
    usuarios en una lista de llaves."""
    correo = "invitado.hash@nutrientrena-qa.com"
    _uid, codigo = _invitar(client, admin_headers, "Invitado Hash", correo)
    assert codigo and len(codigo) >= 8

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == correo).first()
        assert u.invite_code_hash and u.invite_code_hash != codigo
        assert codigo not in u.invite_code_hash
    finally:
        db.close()

    # Y el listado del equipo no lo reparte
    equipo = client.get("/api/admin/team", headers=admin_headers).json()["data"]
    assert codigo not in str(equipo)


def test_el_codigo_no_distingue_mayusculas_ni_espacios(client, seed, admin_headers):
    """Se dicta por teléfono y se copia de un chat: exigir que venga clavado
    solo sirve para que la gente crea que el código está mal."""
    correo = "invitado.formato@nutrientrena-qa.com"
    _uid, codigo = _invitar(client, admin_headers, "Invitado Formato", correo)

    assert _aceptar(client, correo, f"  {codigo.lower()}  ").status_code == 200
    assert _entrar(client, correo, "MiPropia2026!").status_code == 200


# ── Lo que no puede pasar ───────────────────────────────────────────────────

def test_sin_codigo_correcto_no_se_reclama_la_cuenta(client, seed, admin_headers):
    """El punto de todo esto. Con solo el correo, cualquiera se quedaría con
    una cuenta de super-admin ajena."""
    correo = "invitado.blindado@nutrientrena-qa.com"
    _uid, _codigo = _invitar(client, admin_headers, "Invitado Blindado", correo)

    for intento in ["", "ABCD-1234", "0000-0000", "no-es-un-codigo"]:
        r = _aceptar(client, correo, intento, password="Colado123!")
        assert r.status_code == 400, (intento, r.text)

    # Y la cuenta sigue sin abrirse con lo que el atacante puso
    assert _entrar(client, correo, "Colado123!").status_code == 401


def test_el_error_es_el_mismo_exista_o_no_el_correo(client, seed, admin_headers):
    """Distinguirlos convertiría esto en una forma de averiguar qué correos hay
    dados de alta y cuáles están pendientes de reclamar, que es justo lo que le
    interesa a quien quiera colarse."""
    correo = "invitado.enumera@nutrientrena-qa.com"
    _uid, _codigo = _invitar(client, admin_headers, "Invitado Enumera", correo)

    existe = _aceptar(client, correo, "MAL-CODE")
    no_existe = _aceptar(client, "no.existe.nadie@nutrientrena-qa.com", "MAL-CODE")

    assert existe.status_code == no_existe.status_code == 400
    assert existe.json()["message"] == no_existe.json()["message"]


def test_el_codigo_es_de_un_solo_uso(client, seed, admin_headers):
    """Si no, el mismo papelito serviría para volver a cambiarle la contraseña
    más adelante."""
    correo = "invitado.unauso@nutrientrena-qa.com"
    _uid, codigo = _invitar(client, admin_headers, "Invitado Un Uso", correo)

    assert _aceptar(client, correo, codigo, password="Primera123!").status_code == 200
    r = _aceptar(client, correo, codigo, password="Segunda123!")
    assert r.status_code == 400, r.text

    # Sigue valiendo la primera
    assert _entrar(client, correo, "Primera123!").status_code == 200
    assert _entrar(client, correo, "Segunda123!").status_code == 401


def test_un_codigo_caducado_no_vale(client, seed, admin_headers, db):
    correo = "invitado.caducado@nutrientrena-qa.com"
    _uid, codigo = _invitar(client, admin_headers, "Invitado Caducado", correo)
    _caducar(correo, db)

    assert _aceptar(client, correo, codigo).status_code == 400
    assert _entrar(client, correo, "MiPropia2026!").status_code == 401


def test_quien_ya_entro_no_puede_reclamar_su_cuenta_otra_vez(client, seed, admin_headers):
    """A quien ya tiene contraseña no se le regala una segunda vía de entrar:
    si la perdió, el camino es la recuperación de siempre."""
    correo = "invitado.veterano@nutrientrena-qa.com"
    _uid, codigo = _invitar(client, admin_headers, "Invitado Veterano", correo)
    _aceptar(client, correo, codigo, password="Suya123!")
    assert _entrar(client, correo, "Suya123!").status_code == 200

    # Aunque alguien se hubiera guardado el código, ya no sirve
    assert _aceptar(client, correo, codigo, password="Robada123!").status_code == 400


def test_un_coach_normal_no_puede_reclamarse_por_esta_via(client, seed, admin_headers):
    """Solo vale para cuentas invitadas y sin estrenar: un usuario creado por
    el camino normal no tiene código, y esto no puede ser una puerta trasera
    para cambiarle la contraseña a nadie."""
    _uid, _det, _h = _crear_usuario(client, admin_headers, "coach.normal.inv@nutrientrena-qa.com", role_id=5)
    r = _aceptar(client, "coach.normal.inv@nutrientrena-qa.com", "ABCD-1234", password="Robada123!")
    assert r.status_code == 400, r.text
    assert _entrar(client, "coach.normal.inv@nutrientrena-qa.com", "Robada123!").status_code == 401


def test_la_contrasena_tiene_un_minimo(client, seed, admin_headers):
    correo = "invitado.clavecorta@nutrientrena-qa.com"
    _uid, codigo = _invitar(client, admin_headers, "Invitado Clave Corta", correo)
    assert _aceptar(client, correo, codigo, password="123").status_code == 400
    # Y el código no se ha quemado por el intento fallido
    assert _aceptar(client, correo, codigo, password="Bastante123!").status_code == 200


# ── Regenerar el código ─────────────────────────────────────────────────────

def test_se_puede_generar_otro_codigo_si_se_pierde(client, seed, admin_headers):
    correo = "invitado.otrocodigo@nutrientrena-qa.com"
    uid, viejo = _invitar(client, admin_headers, "Invitado Otro Código", correo)

    r = client.post(f"/api/admin/team/{uid}/invite-code", headers=admin_headers)
    assert r.status_code == 200, r.text
    nuevo = r.json()["data"]["codigo_invitacion"]
    assert nuevo != viejo

    # El viejo deja de valer en cuanto se genera otro
    assert _aceptar(client, correo, viejo).status_code == 400
    assert _aceptar(client, correo, nuevo).status_code == 200


def test_no_se_regenera_el_codigo_de_quien_ya_entro(client, seed, admin_headers):
    """Sería darle a quien administra una vía para entrar en la cuenta de otro
    sin que se entere."""
    correo = "invitado.yaentro@nutrientrena-qa.com"
    uid, codigo = _invitar(client, admin_headers, "Invitado Ya Entró", correo)
    _aceptar(client, correo, codigo, password="Suya123!")
    _entrar(client, correo, "Suya123!")

    r = client.post(f"/api/admin/team/{uid}/invite-code", headers=admin_headers)
    assert r.status_code == 400, r.text
    assert "olvidado" in r.json()["message"].lower()


def test_solo_el_superadmin_genera_codigos(client, seed, admin_headers):
    from tests.test_admin_panel import _con_rol

    correo = "invitado.permiso@nutrientrena-qa.com"
    uid, _codigo = _invitar(client, admin_headers, "Invitado Permiso", correo)

    _u, _d, h = _con_rol(client, admin_headers, "soporte.codigo@nutrientrena-qa.com", SOPORTE)
    assert client.post(f"/api/admin/team/{uid}/invite-code", headers=h).status_code == 403


def test_poner_la_contrasena_a_mano_no_genera_codigo(client, seed, admin_headers):
    """Si quien invita ya le entrega la contraseña, un código suelto sería una
    segunda llave que nadie necesita."""
    r = client.post("/api/admin/team", headers=admin_headers, json={
        "name": "Con Clave Directa", "email": "con.clave.directa@nutrientrena-qa.com",
        "role_id": SOPORTE, "password": "Directa123!"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["codigo_invitacion"] is None
