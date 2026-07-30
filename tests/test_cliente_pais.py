from app.database import SessionLocal
from app.models.country import Country
from app.models.user import User, UserDetail
from tests.test_org_scope import _crear_usuario


def test_editar_cliente_guarda_el_pais(client, seed, admin_headers):
    """El modal de editar cliente manda country_code; comprobamos que llega."""
    db = SessionLocal()
    try:
        if not db.query(Country).filter(Country.code == "ES").first():
            db.add(Country(code="ES", country="España")); db.commit()
    finally:
        db.close()

    uid, det, _h = _crear_usuario(client, admin_headers, "cliente.pais@nutrientrena-qa.com", role_id=6)

    r = client.put(f"/api/users/{det}/update", headers=admin_headers, json={"country_code": "ES"})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        assert db.query(UserDetail).filter(UserDetail.id == det).first().country_code == "ES"
    finally:
        db.close()

    # Y se devuelve con su nombre para poder pintarlo
    r = client.get(f"/api/users/{det}/edit", headers=admin_headers)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["country_code"] == "ES"
    assert (d.get("country") or {}).get("country") == "España", d.get("country")
