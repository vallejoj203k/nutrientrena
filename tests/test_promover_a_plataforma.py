"""Promover contenido de una organización al catálogo de plataforma.

El pie del diagrama de jerarquía lo pide: el super-admin ve el contenido de
todas las organizaciones y "promueve lo bueno a Plataforma". Ver sí podía;
promover no existía en ningún sitio.
"""
from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.routine import Routine
from app.models.training import Training

from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _coach_con_org(client, admin_headers, sufijo):
    uid, det, h = _crear_usuario(client, admin_headers, f"coach.{sufijo}@nutrientrena-qa.com", role_id=5)
    org_id = _crear_organizacion(det, f"Organización {sufijo}")
    return org_id, h


def _mover(client, headers, tipo, id_, destino):
    return client.put(f"/api/content/{tipo}/{id_}/organization",
                      headers=headers, json={"organization_id": destino})


# ── El caso que pide el diagrama ───────────────────────────────────────────

def test_el_superadmin_promueve_una_rutina_al_catalogo_comun(client, seed, admin_headers):
    org, h = _coach_con_org(client, admin_headers, "promo-rutina")
    r = client.post("/api/routines", headers=h, json={"name": "Rutina buena del equipo"})
    rid = r.json()["data"]["id"]

    db = SessionLocal()
    try:
        assert db.get(Routine, rid).organization_id == org, "debería nacer en su organización"
    finally:
        db.close()

    r = _mover(client, admin_headers, "routine", rid, None)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["organization_id"] is None
    assert r.json()["data"]["organization_id_anterior"] == org

    db = SessionLocal()
    try:
        assert db.get(Routine, rid).organization_id is None
    finally:
        db.close()


def test_lo_promovido_lo_ve_otra_organizacion(client, seed, admin_headers):
    """El sentido de promover: que sirva de base a todas."""
    _org_a, h_a = _coach_con_org(client, admin_headers, "promo-origen")
    _org_b, h_b = _coach_con_org(client, admin_headers, "promo-ajena")

    rid = client.post("/api/routines", headers=h_a, json={"name": "Rutina que se promueve"}).json()["data"]["id"]

    nombres = [x["name"] for x in client.get("/api/routines/findAll", headers=h_b).json()["data"]]
    assert "Rutina que se promueve" not in nombres, "antes de promover no debería verla"

    assert _mover(client, admin_headers, "routine", rid, None).status_code == 200

    nombres = [x["name"] for x in client.get("/api/routines/findAll", headers=h_b).json()["data"]]
    assert "Rutina que se promueve" in nombres, "tras promover, toda organización debería verla"


def test_la_organizacion_de_origen_no_lo_pierde(client, seed, admin_headers):
    org, h = _coach_con_org(client, admin_headers, "promo-no-pierde")
    rid = client.post("/api/routines", headers=h, json={"name": "Rutina promovida sin perderla"}).json()["data"]["id"]
    assert _mover(client, admin_headers, "routine", rid, None).status_code == 200

    nombres = [x["name"] for x in client.get("/api/routines/findAll", headers=h).json()["data"]]
    assert "Rutina promovida sin perderla" in nombres


def test_es_reversible(client, seed, admin_headers):
    """Una promoción por error sin vuelta atrás sería una trampa."""
    org, h = _coach_con_org(client, admin_headers, "promo-reversible")
    rid = client.post("/api/routines", headers=h, json={"name": "Rutina de ida y vuelta"}).json()["data"]["id"]

    assert _mover(client, admin_headers, "routine", rid, None).status_code == 200
    r = _mover(client, admin_headers, "routine", rid, org)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["organization_id"] == org


# ── Los cuatro tipos de contenido ──────────────────────────────────────────

def test_funciona_con_alimentos_y_ejercicios(client, seed, admin_headers):
    org, h = _coach_con_org(client, admin_headers, "promo-tipos")

    aid = client.post("/api/aliments", headers=h, json={
        "name": "Alimento promovible", "calories": 100, "proteins": 10,
        "carbohydrates": 10, "fats": 2}).json()["data"]["id"]
    tid = client.post("/api/trainings", headers=h, json={"name": "Ejercicio promovible"}).json()["data"]["id"]

    assert _mover(client, admin_headers, "aliment", aid, None).status_code == 200
    assert _mover(client, admin_headers, "training", tid, None).status_code == 200

    db = SessionLocal()
    try:
        assert db.get(Aliment, aid).organization_id is None
        assert db.get(Training, tid).organization_id is None
    finally:
        db.close()


# ── Quién NO puede ────────────────────────────────────────────────────────

def test_un_coach_no_puede_promover_ni_lo_suyo(client, seed, admin_headers):
    """Regalar contenido al resto de la plataforma es decisión de la
    administración, no del que lo creó."""
    _org, h = _coach_con_org(client, admin_headers, "promo-coach")
    rid = client.post("/api/routines", headers=h, json={"name": "Rutina que el coach no promueve"}).json()["data"]["id"]
    assert _mover(client, h, "routine", rid, None).status_code == 403


def test_un_duenio_de_organizacion_tampoco(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "admin.promo@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det, "Organización que no promueve")
    rid = client.post("/api/routines", headers=h, json={"name": "Rutina del dueño"}).json()["data"]["id"]
    assert _mover(client, h, "routine", rid, None).status_code == 403


def test_no_se_puede_mover_a_una_organizacion_inexistente(client, seed, admin_headers):
    org, h = _coach_con_org(client, admin_headers, "promo-destino-malo")
    rid = client.post("/api/routines", headers=h, json={"name": "Rutina destino inválido"}).json()["data"]["id"]
    assert _mover(client, admin_headers, "routine", rid, "no-existe").status_code == 404


def test_tipo_no_valido_y_contenido_inexistente(client, seed, admin_headers):
    assert _mover(client, admin_headers, "invento", "1", None).status_code == 400
    assert _mover(client, admin_headers, "routine", "999999", None).status_code == 404
    # id no numérico en un modelo de id entero: 404, no un error de servidor
    assert _mover(client, admin_headers, "routine", "abc", None).status_code == 404


def test_promover_algo_que_ya_es_de_plataforma_avisa(client, seed, admin_headers):
    rid = client.post("/api/routines", headers=admin_headers, json={"name": "Rutina ya global"}).json()["data"]["id"]
    r = _mover(client, admin_headers, "routine", rid, None)
    assert r.status_code == 400, r.text
    assert "plataforma" in r.json().get("message", "").lower()
