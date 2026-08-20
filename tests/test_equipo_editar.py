"""Editar los datos de alguien del equipo de Alzum.

La pantalla ya dejaba cambiar el ROL y sacar a la persona del equipo, pero no
tocar sus datos: una errata en un apellido, o un correo mal escrito al
invitar, no se podían arreglar desde ninguna parte de la aplicación.

Lo que se comprueba aquí, además de que guarde:

  · Que la contraseña en blanco signifique "no la toques". Es la trampa de
    cualquier formulario de edición con contraseña: guardar el nombre no puede
    dejar la cuenta con la contraseña vacía ni con una nueva sin querer.
  · Que solo se pueda editar a quien está EN EL EQUIPO. La ruta recibe un
    user_id, y sin esa comprobación una pantalla que solo habla del equipo
    interno serviría para cambiarle la contraseña a cualquier coach.
  · Que quien no tiene acceso a la sección no entre.
"""
import uuid

from app.database import SessionLocal
from app.models.user import User

from tests.test_org_scope import _crear_coach


def _invitar(client, admin_headers, suf, role_id=7, clave="Editor123!"):
    r = client.post("/api/admin/team", headers=admin_headers, json={
        "name": f"Miembro {suf}", "email": f"equipo.{suf}@nutrientrena-qa.com",
        "role_id": role_id, "password": clave,
    })
    assert r.status_code == 200, r.text
    return r.json()["data"]["user_id"]


def _entra(client, correo, clave):
    return client.post("/api/auth/login", json={"email": correo, "password": clave})


def test_se_corrigen_los_datos_del_alta(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    uid = _invitar(client, admin_headers, suf)

    r = client.put(f"/api/admin/team/{uid}", headers=admin_headers, json={
        "name": "Lucía", "last_name": "Prats Gómez",
        "email": f"lucia.{suf}@alzum.io", "phone": "600112233",
    })
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["nombre"] == "Lucía" and d["apellidos"] == "Prats Gómez", d
    assert d["email"] == f"lucia.{suf}@alzum.io" and d["phone"] == "600112233", d

    # Y el listado lo cuenta igual, que es de donde se rellena el formulario.
    equipo = client.get("/api/admin/team", headers=admin_headers).json()["data"]["miembros"]
    fila = next(m for m in equipo if m["user_id"] == uid)
    assert fila["name"] == "Lucía Prats Gómez", fila


def test_la_contraseña_se_cambia_y_la_vieja_deja_de_valer(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    uid = _invitar(client, admin_headers, suf)
    correo = f"equipo.{suf}@nutrientrena-qa.com"
    assert _entra(client, correo, "Editor123!").status_code == 200

    r = client.put(f"/api/admin/team/{uid}", headers=admin_headers,
                   json={"password": "NuevaClave456!"})
    assert r.status_code == 200, r.text

    assert _entra(client, correo, "NuevaClave456!").status_code == 200
    assert _entra(client, correo, "Editor123!").status_code != 200


def test_dejarla_en_blanco_NO_toca_la_contraseña(client, seed, admin_headers):
    """La trampa del formulario: guardar el nombre no puede cambiar el acceso."""
    suf = uuid.uuid4().hex[:8]
    uid = _invitar(client, admin_headers, suf)
    correo = f"equipo.{suf}@nutrientrena-qa.com"

    for vacio in (None, ""):
        r = client.put(f"/api/admin/team/{uid}", headers=admin_headers,
                       json={"name": "Nombre nuevo", "password": vacio})
        assert r.status_code == 200, r.text
        assert _entra(client, correo, "Editor123!").status_code == 200, vacio


def test_una_contraseña_corta_se_rechaza(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    uid = _invitar(client, admin_headers, suf)
    r = client.put(f"/api/admin/team/{uid}", headers=admin_headers, json={"password": "123"})
    assert r.status_code == 400, r.text
    # Y no la ha cambiado a medias.
    assert _entra(client, f"equipo.{suf}@nutrientrena-qa.com", "Editor123!").status_code == 200


def test_no_se_puede_poner_el_correo_de_otro(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    uid_a = _invitar(client, admin_headers, suf + "a")
    _invitar(client, admin_headers, suf + "b")

    r = client.put(f"/api/admin/team/{uid_a}", headers=admin_headers,
                   json={"email": f"equipo.{suf}b@nutrientrena-qa.com"})
    assert r.status_code == 400, r.text


def test_guardar_su_propio_correo_no_falla(client, seed, admin_headers):
    """Cambiar solo el nombre manda el correo tal cual: si la comprobación de
    duplicados no se excluye a sí misma, editar cualquier cosa es imposible."""
    suf = uuid.uuid4().hex[:8]
    uid = _invitar(client, admin_headers, suf)
    r = client.put(f"/api/admin/team/{uid}", headers=admin_headers, json={
        "name": "Otro nombre", "email": f"equipo.{suf}@nutrientrena-qa.com"})
    assert r.status_code == 200, r.text


def test_no_sirve_para_editar_a_quien_no_es_del_equipo(client, seed, admin_headers):
    """Con el id de un coach a mano se le estaría cambiando la contraseña desde
    una pantalla que solo habla del equipo interno."""
    suf = uuid.uuid4().hex[:8]
    uid_coach, _det, _h = _crear_coach(client, admin_headers, f"coach.eq.{suf}@nutrientrena-qa.com")

    r = client.put(f"/api/admin/team/{uid_coach}", headers=admin_headers,
                   json={"password": "MeCuelo123!"})
    assert r.status_code == 404, r.text


def test_un_coach_no_edita_al_equipo_de_la_plataforma(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    uid = _invitar(client, admin_headers, suf)
    _u, _d, h_coach = _crear_coach(client, admin_headers, f"fuera.eq.{suf}@nutrientrena-qa.com")

    r = client.put(f"/api/admin/team/{uid}", headers=h_coach, json={"password": "Cualquiera1!"})
    assert r.status_code == 403, r.text


def test_ponerle_contraseña_anula_el_codigo_de_invitacion(client, seed, admin_headers):
    """Si se le acaba de dar una contraseña, no debe quedar abierta además una
    puerta de un solo uso que nadie recuerda haber dejado abierta."""
    suf = uuid.uuid4().hex[:8]
    # Sin contraseña → se le genera código de invitación.
    r = client.post("/api/admin/team", headers=admin_headers, json={
        "name": f"Invitado {suf}", "email": f"inv.{suf}@nutrientrena-qa.com", "role_id": 7})
    assert r.status_code == 200, r.text
    uid = r.json()["data"]["user_id"]
    assert r.json()["data"]["codigo_invitacion"], r.json()["data"]

    db = SessionLocal()
    try:
        assert db.query(User).filter(User.id == uid).first().invite_code_hash is not None
    finally:
        db.close()

    client.put(f"/api/admin/team/{uid}", headers=admin_headers, json={"password": "YaTieneClave1!"})

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == uid).first()
        assert u.invite_code_hash is None and u.invite_expires_at is None
    finally:
        db.close()
    assert _entra(client, f"inv.{suf}@nutrientrena-qa.com", "YaTieneClave1!").status_code == 200


def test_el_nombre_no_se_puede_dejar_vacio(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    uid = _invitar(client, admin_headers, suf)
    r = client.put(f"/api/admin/team/{uid}", headers=admin_headers, json={"name": "   "})
    assert r.status_code == 400, r.text
