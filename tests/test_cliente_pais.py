"""country_code guarda el NOMBRE del país, no un código ISO.

Pese al nombre de la columna, la migración v0w1x2y3z4a5 ("Allow free-text
country names") quitó la clave foránea a countries.code y ensanchó el campo a
100 caracteres. El modelo, sin embargo, se había quedado declarando
String(10) + ForeignKey: los tests creaban el esquema con create_all y
validaban una tabla que producción no tiene.

Además las dos pantallas de alta guardaban formatos distintos —una el nombre y
otra el código— en la misma columna.
"""
from app.database import SessionLocal
from app.models.country import Country
from app.models.user import UserDetail

from tests.test_org_scope import _crear_usuario


def _asegurar_pais(code, nombre):
    db = SessionLocal()
    try:
        if not db.query(Country).filter(Country.code == code).first():
            db.add(Country(code=code, country=nombre))
            db.commit()
    finally:
        db.close()


def test_el_pais_se_guarda_como_nombre(client, seed, admin_headers):
    _asegurar_pais("ES", "España")
    _uid, det, _h = _crear_usuario(client, admin_headers, "cliente.pais.nombre@nutrientrena-qa.com", role_id=6)

    r = client.put(f"/api/users/{det}/update", headers=admin_headers, json={"country_code": "España"})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        assert db.query(UserDetail).filter(UserDetail.id == det).first().country_code == "España"
    finally:
        db.close()

    assert client.get(f"/api/users/{det}/edit", headers=admin_headers).json()["data"]["country_code"] == "España"


def test_admite_nombres_largos_y_acentuados(client, seed, admin_headers):
    """El campo es String(100): antes el modelo decía 10 y estos no cabían."""
    largo = "República Democrática del Congo"
    _asegurar_pais("CD", largo)
    _uid, det, _h = _crear_usuario(client, admin_headers, "cliente.pais.largo@nutrientrena-qa.com", role_id=6)

    r = client.put(f"/api/users/{det}/update", headers=admin_headers, json={"country_code": largo})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/users/{det}/edit", headers=admin_headers).json()["data"]["country_code"] == largo


def test_una_ficha_antigua_con_el_codigo_sigue_resolviendo_su_nombre(client, seed, admin_headers):
    """No se migran los valores viejos: la relación los resuelve para poder
    seguir enseñando el nombre."""
    _asegurar_pais("PT", "Portugal")
    _uid, det, _h = _crear_usuario(client, admin_headers, "cliente.pais.codigo@nutrientrena-qa.com", role_id=6)

    r = client.put(f"/api/users/{det}/update", headers=admin_headers, json={"country_code": "PT"})
    assert r.status_code == 200, r.text

    d = client.get(f"/api/users/{det}/edit", headers=admin_headers).json()["data"]
    assert d["country_code"] == "PT"
    assert (d.get("country") or {}).get("country") == "Portugal", d.get("country")


def test_un_pais_fuera_del_catalogo_no_rompe(client, seed, admin_headers):
    """Sin clave foránea, un valor que no esté en countries se guarda igual."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "cliente.pais.raro@nutrientrena-qa.com", role_id=6)

    r = client.put(f"/api/users/{det}/update", headers=admin_headers, json={"country_code": "Tierra Media"})
    assert r.status_code == 200, r.text
    d = client.get(f"/api/users/{det}/edit", headers=admin_headers).json()["data"]
    assert d["country_code"] == "Tierra Media"
    assert d.get("country") is None
