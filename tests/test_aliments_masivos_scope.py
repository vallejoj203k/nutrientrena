"""Los endpoints de escritura masiva de alimentos respetan la organización.

Se cerró el hueco de editar un alimento ajeno, pero quedaron cuatro puertas
abiertas al mismo sitio: borrar no comprobaba nada, y importar, sincronizar con
USDA y clasificar momentos recorrían TODO el catálogo. Un coach podía borrar o
reescribir los alimentos privados de otra organización.
"""
from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.group_food import GroupFood

from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _alimento_de(client, headers, name, **extra):
    r = client.post("/api/aliments", headers=headers, json={
        "name": name, "calories": 100, "proteins": 10,
        "carbohydrates": 10, "fats": 2, **extra})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _grupo_frutas():
    """Un grupo que el clasificador SÍ reconoce.

    Sin grupo, moments_from_group no deduce nada y hace falta la IA, que en los
    tests no está configurada: la comprobación de "no toca lo ajeno" pasaría en
    vacío porque no se escribiría nada de todas formas.
    """
    db = SessionLocal()
    try:
        g = db.query(GroupFood).filter(GroupFood.name == "Frutas").first()
        if not g:
            g = GroupFood(name="Frutas")
            db.add(g)
            db.commit()
            db.refresh(g)
        return g.id
    finally:
        db.close()


def _org_de(cliente, admin_headers, sufijo, role_id=5):
    uid, det, h = _crear_usuario(cliente, admin_headers, f"coach.{sufijo}@nutrientrena-qa.com", role_id=role_id)
    org_id = _crear_organizacion(det, f"Organización {sufijo}")
    return org_id, h


# ── Borrado ────────────────────────────────────────────────────────────────

def test_no_se_puede_borrar_el_alimento_de_otra_organizacion(client, seed, admin_headers):
    _org_a, h_a = _org_de(client, admin_headers, "borrado-a")
    _org_b, h_b = _org_de(client, admin_headers, "borrado-b")

    aid = _alimento_de(client, h_a, "Alimento privado de A (borrado)")
    assert client.delete(f"/api/aliments/{aid}", headers=h_b).status_code == 403

    # Su dueño sí puede
    assert client.delete(f"/api/aliments/{aid}", headers=h_a).status_code == 200


def test_un_coach_no_puede_borrar_del_catalogo_de_plataforma(client, seed, admin_headers):
    aid = _alimento_de(client, admin_headers, "Alimento de plataforma (borrado)")
    _org, h = _org_de(client, admin_headers, "borrado-plataforma")
    assert client.delete(f"/api/aliments/{aid}", headers=h).status_code == 403
    # El superadmin sigue pudiendo
    assert client.delete(f"/api/aliments/{aid}", headers=admin_headers).status_code == 200


# ── Clasificación masiva de momentos ───────────────────────────────────────

def test_clasificar_momentos_si_toca_los_propios(client, seed, admin_headers):
    """Primero se demuestra que el clasificador SÍ escribe cuando el alimento
    está en alcance; si no, la prueba de abajo no valdría nada."""
    grupo = _grupo_frutas()
    _org_a, h_a = _org_de(client, admin_headers, "momentos-propios")
    aid = _alimento_de(client, h_a, "Manzana propia", group_food_id=grupo)

    r = client.post("/api/aliments/classify-moments", headers=h_a,
                    json={"ids": [aid], "force": True})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["classified"] == 1, r.json()

    db = SessionLocal()
    try:
        assert db.get(Aliment, aid).meal_moments, "el clasificador no escribió nada"
    finally:
        db.close()


def test_clasificar_momentos_no_toca_alimentos_de_otra_organizacion(client, seed, admin_headers):
    grupo = _grupo_frutas()
    _org_a, h_a = _org_de(client, admin_headers, "momentos-a")
    _org_b, h_b = _org_de(client, admin_headers, "momentos-b")

    aid = _alimento_de(client, h_a, "Manzana privada de A", group_food_id=grupo)

    # B intenta clasificar el alimento de A pasándole el id directamente
    r = client.post("/api/aliments/classify-moments", headers=h_b,
                    json={"ids": [aid], "force": True})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["classified"] == 0, "B ha clasificado un alimento de A"

    db = SessionLocal()
    try:
        assert db.get(Aliment, aid).meal_moments is None, "B ha reescrito un alimento de A"
    finally:
        db.close()


def test_el_superadmin_sigue_clasificando_todo(client, seed, admin_headers):
    grupo = _grupo_frutas()
    _org_a, h_a = _org_de(client, admin_headers, "momentos-superadmin")
    aid = _alimento_de(client, h_a, "Fruta que clasifica el superadmin", group_food_id=grupo)

    r = client.post("/api/aliments/classify-moments", headers=admin_headers,
                    json={"ids": [aid], "force": True})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["classified"] == 1, r.json()


# ── Importación CSV ────────────────────────────────────────────────────────

def test_lo_importado_por_csv_queda_en_la_organizacion(client, seed, admin_headers):
    org_a, h_a = _org_de(client, admin_headers, "csv-a")
    csv = "nombre,calorias,proteinas,carbohidratos,grasas\nAlimento CSV de A,120,12,10,3\n"

    r = client.post("/api/aliments/import", headers=h_a,
                    files={"file": ("a.csv", csv, "text/csv")})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        obj = db.query(Aliment).filter(Aliment.name == "Alimento CSV de A").first()
        assert obj is not None, "no se importó"
        assert obj.organization_id == org_a, obj.organization_id
    finally:
        db.close()


def test_lo_importado_por_el_superadmin_va_al_catalogo_comun(client, seed, admin_headers):
    csv = "nombre,calorias,proteinas,carbohidratos,grasas\nAlimento CSV de plataforma,90,9,9,1\n"
    r = client.post("/api/aliments/import", headers=admin_headers,
                    files={"file": ("p.csv", csv, "text/csv")})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        obj = db.query(Aliment).filter(Aliment.name == "Alimento CSV de plataforma").first()
        assert obj is not None and obj.organization_id is None
    finally:
        db.close()
