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


# ── Hallazgos de la revisión del PR ────────────────────────────────────────
# Dos agujeros que dejó la primera versión de este scope y que solo se vieron
# al revisar el PR entero.

def test_el_autor_puede_editar_y_borrar_su_alimento_sin_organizacion(client, seed, admin_headers):
    """Un coach sin organización crea con organization_id NULL, así que su
    propio alimento quedaba marcado como "de plataforma" y la regla que
    protege el catálogo común le bloqueaba lo que acababa de crear. Es el
    mismo fallo que ya se corrigió en rutinas y dietas (Fase 1b).

    Además, antes del scope de borrado ese coach SÍ podía borrarlo (no había
    comprobación ninguna), así que cerrar el hueco sin la regla del autor fue
    una regresión."""
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.autor.alimento@nutrientrena-qa.com", role_id=5)
    aid = _alimento_de(client, h, "Alimento de un coach suelto")

    r = client.put(f"/api/aliments/{aid}/update", headers=h, json={"name": "Corregido por su autor"})
    assert r.status_code == 200, r.text
    assert client.delete(f"/api/aliments/{aid}", headers=h).status_code == 200


def test_en_masa_no_se_puede_tocar_lo_que_no_se_puede_tocar_uno_a_uno(client, seed, admin_headers):
    """El acotado masivo incluía el contenido de plataforma, así que un coach
    recibía 403 al editar un alimento del catálogo común uno a uno pero podía
    reescribirlo entero con una sola llamada a classify-moments."""
    grupo = _grupo_frutas()
    aid = _alimento_de(client, admin_headers, "Fruta del catálogo común", group_food_id=grupo)

    _org, h = _org_de(client, admin_headers, "masivo-vs-individual")

    # Uno a uno: bloqueado
    assert client.put(f"/api/aliments/{aid}/update", headers=h, json={"name": "Intento"}).status_code == 403

    # En masa: tiene que estar bloqueado igual
    r = client.post("/api/aliments/classify-moments", headers=h, json={"ids": [aid], "force": True})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["classified"] == 0, "se ha clasificado contenido de plataforma"

    db = SessionLocal()
    try:
        assert db.get(Aliment, aid).meal_moments is None, "se ha reescrito el catálogo común"
    finally:
        db.close()


def test_el_editor_de_contenido_global_si_puede_en_masa(client, seed, admin_headers):
    """Regresión: para el editor de contenido global el catálogo común es
    justamente su trabajo, también en las operaciones masivas."""
    from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL
    from app.seeds.roles import seed_roles
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()

    grupo = _grupo_frutas()
    aid = _alimento_de(client, admin_headers, "Fruta que clasifica el editor", group_food_id=grupo)
    _uid, _det, h = _crear_usuario(client, admin_headers, "editor.masivo@nutrientrena-qa.com",
                                   role_id=EDITOR_CONTENIDO_GLOBAL)

    r = client.post("/api/aliments/classify-moments", headers=h, json={"ids": [aid], "force": True})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["classified"] == 1, r.json()
