"""Corregir los datos de un miembro del equipo.

Se podía añadir a alguien a la organización pero no cambiarle nada después: el
lápiz solo abría los permisos, y la ficha ni siquiera enseñaba su correo —había
un "Coach empleado" fijo, igual para todos—. Si te equivocabas al escribir el
email al darle de alta, no había forma de verlo ni de arreglarlo.

El endpoint vive en el router de organizaciones y no se reutiliza
`PUT /users/{id}/update` porque aquel comprueba el acceso A CLIENTES: un dueño
que además es coach no pasa esa puerta para tocar a alguien de su equipo, que
no es cliente suyo. La pregunta correcta aquí es otra —¿es tuya esta
organización y es tuyo este miembro?— y es la que se comprueba.
"""
import uuid

from app.database import SessionLocal
from app.models.organization import Organization, OrganizationMember
from app.models.user import User, UserDetail

from tests.test_org_scope import _crear_coach, _crear_organizacion, _crear_usuario


def _monta_equipo(client, admin_headers, suf):
    """Un dueño con su organización y un miembro dentro."""
    _uid, det_duenio, h_duenio = _crear_coach(
        client, admin_headers, f"duenio.mi.{suf}@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_duenio, f"Centro Miembros {suf}")

    r = client.post(f"/api/organizations/{org_id}/members/create-coach",
                    headers=h_duenio,
                    json={"name": "Ana", "last_name": "Pérez",
                          "email": f"ana.{suf}@nutrientrena-qa.com",
                          "password": "Coach123!", "permissions": {}})
    assert r.status_code == 200, r.text
    return org_id, h_duenio, r.json()["data"]["member_id"]


# ── Ver quién es ───────────────────────────────────────────────────────────

def test_el_listado_dice_el_correo_de_cada_miembro(client, seed, admin_headers):
    """Sin esto, la ficha no identificaba a nadie: enseñaba un texto fijo."""
    suf = uuid.uuid4().hex[:8]
    org_id, h, _mid = _monta_equipo(client, admin_headers, suf)

    r = client.get(f"/api/organizations/{org_id}/members", headers=h)
    assert r.status_code == 200, r.text
    m = r.json()["data"][0]
    assert m["email"] == f"ana.{suf}@nutrientrena-qa.com", m
    # Nombre y apellido por separado: la ficha rellena un campo con cada uno, y
    # partir el nombre completo por el espacio se equivoca con "Ana María".
    assert m["first_name"] == "Ana" and m["last_name"] == "Pérez", m


# ── Editar ─────────────────────────────────────────────────────────────────

def test_el_duenio_cambia_los_datos_del_miembro(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org_id, h, mid = _monta_equipo(client, admin_headers, suf)

    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h,
                   json={"name": "Ana María", "last_name": "Pérez Gil",
                         "email": f"ana.bien.{suf}@nutrientrena-qa.com",
                         "phone": "600111222"})
    assert r.status_code == 200, r.text

    m = client.get(f"/api/organizations/{org_id}/members", headers=h).json()["data"][0]
    assert m["first_name"] == "Ana María"
    assert m["email"] == f"ana.bien.{suf}@nutrientrena-qa.com"
    assert m["phone"] == "600111222"


def test_la_contrasenia_nueva_es_la_que_vale(client, seed, admin_headers):
    """Lo que de verdad hay que comprobar no es que responda 200: es que con la
    nueva se entra y con la vieja ya no."""
    suf = uuid.uuid4().hex[:8]
    org_id, h, mid = _monta_equipo(client, admin_headers, suf)
    correo = f"ana.{suf}@nutrientrena-qa.com"

    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h,
                   json={"password": "NuevaClave1!"})
    assert r.status_code == 200, r.text

    assert client.post("/api/auth/login",
                       json={"email": correo, "password": "NuevaClave1!"}).status_code == 200
    assert client.post("/api/auth/login",
                       json={"email": correo, "password": "Coach123!"}).status_code != 200


def test_dejar_la_contrasenia_vacia_no_la_cambia(client, seed, admin_headers):
    """En la pantalla, el campo en blanco significa "no la toques". Si eso
    borrara la contraseña, el miembro se quedaría fuera sin que nadie lo supiera."""
    suf = uuid.uuid4().hex[:8]
    org_id, h, mid = _monta_equipo(client, admin_headers, suf)
    correo = f"ana.{suf}@nutrientrena-qa.com"

    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h,
                   json={"name": "Ana", "password": ""})
    assert r.status_code == 200, r.text
    assert client.post("/api/auth/login",
                       json={"email": correo, "password": "Coach123!"}).status_code == 200


def test_no_se_puede_poner_un_correo_que_ya_usa_otra_cuenta(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org_id, h, mid = _monta_equipo(client, admin_headers, suf)
    _uid, _det, _h = _crear_usuario(client, admin_headers,
                                    f"ocupado.{suf}@nutrientrena-qa.com", role_id=5)

    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h,
                   json={"email": f"ocupado.{suf}@nutrientrena-qa.com"})
    assert r.status_code == 400, r.text


def test_guardar_sin_tocar_el_correo_no_falla_por_duplicado(client, seed, admin_headers):
    """El propio correo no cuenta como "ya registrado": si no, cambiar solo el
    nombre sería imposible."""
    suf = uuid.uuid4().hex[:8]
    org_id, h, mid = _monta_equipo(client, admin_headers, suf)

    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h,
                   json={"name": "Anita", "email": f"ana.{suf}@nutrientrena-qa.com"})
    assert r.status_code == 200, r.text


def test_una_contrasenia_corta_se_rechaza(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org_id, h, mid = _monta_equipo(client, admin_headers, suf)
    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h,
                   json={"password": "123"})
    assert r.status_code == 400, r.text


def test_el_nombre_no_se_puede_dejar_en_blanco(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org_id, h, mid = _monta_equipo(client, admin_headers, suf)
    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h,
                   json={"name": "   "})
    assert r.status_code == 400, r.text


# ── Quién puede ────────────────────────────────────────────────────────────

def test_un_miembro_no_puede_editar_a_otro(client, seed, admin_headers):
    """Estar dentro del equipo no es mandar en él."""
    suf = uuid.uuid4().hex[:8]
    org_id, _h_duenio, mid = _monta_equipo(client, admin_headers, suf)

    lg = client.post("/api/auth/login",
                     json={"email": f"ana.{suf}@nutrientrena-qa.com", "password": "Coach123!"})
    assert lg.status_code == 200, lg.text
    h_miembro = {"Authorization": f"Bearer {lg.json()['data']['token']}"}

    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h_miembro,
                   json={"name": "Yo mismo"})
    assert r.status_code == 403, r.text


def test_el_duenio_de_otra_cuenta_tampoco(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org_id, _h, mid = _monta_equipo(client, admin_headers, suf)
    _uid, det_otro, h_otro = _crear_coach(client, admin_headers,
                                          f"otro.duenio.{suf}@nutrientrena-qa.com")
    _crear_organizacion(det_otro, f"Otro Centro {suf}")

    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=h_otro,
                   json={"name": "Intruso"})
    assert r.status_code == 403, r.text


def test_no_se_puede_editar_a_un_miembro_de_otra_organizacion(client, seed, admin_headers):
    """Con el id a mano: el miembro tiene que ser de ESA organización."""
    suf = uuid.uuid4().hex[:8]
    org_a, h_a, _mid_a = _monta_equipo(client, admin_headers, suf)
    org_b, _h_b, mid_b = _monta_equipo(client, admin_headers, suf + "b")

    # El dueño de A intenta editar al miembro de B pasándolo por la ruta de A
    r = client.put(f"/api/organizations/{org_a}/members/{mid_b}", headers=h_a,
                   json={"name": "Robado"})
    assert r.status_code == 404, r.text


def test_el_superadmin_si_puede(client, seed, admin_headers):
    """Soporte de plataforma: si un dueño pierde el acceso, alguien tiene que
    poder arreglarlo."""
    suf = uuid.uuid4().hex[:8]
    org_id, _h, mid = _monta_equipo(client, admin_headers, suf)
    r = client.put(f"/api/organizations/{org_id}/members/{mid}", headers=admin_headers,
                   json={"name": "Corregido"})
    assert r.status_code == 200, r.text
