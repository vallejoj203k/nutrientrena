"""El subtítulo de cada comida: qué se come, no solo cuándo.

El nombre de la comida dice CUÁNDO ("Desayuno", "Cena") y se repite igual en
todas las dietas. Qué se come no estaba en ninguna parte: el cliente tenía que
abrir la comida y leer la lista de alimentos para saber qué le tocaba.

Dos cosas que conviene tener escritas, porque son donde esto se pierde:

  · Al ASIGNAR la dieta a un cliente se hace una copia. Si la copia no se
    llevara el subtítulo, el coach lo vería en su biblioteca y su cliente no —
    justo a quien va dirigido.
  · Una edición parcial que no mande el subtítulo NO lo borra. Mandarlo vacío,
    sí. Sin esa distinción, cambiar solo la hora de una comida se llevaba por
    delante lo escrito.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.diet import DietFood
from app.models.user import UserDetail, UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario


def _monta(client, admin_headers, suf):
    _u, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.sub.{suf}@nutrientrena-qa.com")
    _uid, det_cli, h_cli = _crear_usuario(
        client, admin_headers, f"cli.sub.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        db.commit()
    finally:
        db.close()
    return h_coach, det_cli, h_cli


def _alimento(suf):
    db = SessionLocal()
    try:
        al = Aliment(id=str(uuid.uuid4()), name=f"Huevo {suf}", calories=150.0,
                     proteins=13.0, carbohydrates=1.0, fats=11.0, quantity_unit="g")
        db.add(al)
        db.commit()
        return al.id
    finally:
        db.close()


def _crear_dieta(client, h_coach, suf, subtitulo="Huevos revueltos con aguacate"):
    al = _alimento(suf)
    r = client.post("/api/diets", headers=h_coach, json={
        "title": f"Dieta {suf}",
        "foods": [{"name": "Desayuno", "subtitle": subtitulo, "time": "08:00",
                   "detail": [{"aliment_id": al, "quantity_calc": 100, "order": 0}]}]})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _comidas(client, headers, diet_id):
    r = client.get(f"/api/diets/{diet_id}/edit", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]["foods"]


# ── Lo básico ──────────────────────────────────────────────────────────────

def test_UNA_COMIDA_GUARDA_SU_SUBTITULO(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear_dieta(client, h_coach, suf)

    comida = _comidas(client, h_coach, did)[0]
    assert comida["name"] == "Desayuno", comida
    assert comida["subtitle"] == "Huevos revueltos con aguacate", comida


def test_sin_subtitulo_la_comida_sigue_funcionando(client, seed, admin_headers):
    """Es opcional: quien no lo use no tiene que rellenar nada."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    al = _alimento(suf)
    r = client.post("/api/diets", headers=h_coach, json={
        "title": f"Dieta {suf}",
        "foods": [{"name": "Cena", "time": "21:00",
                   "detail": [{"aliment_id": al, "quantity_calc": 100, "order": 0}]}]})
    assert r.status_code == 200, r.text
    assert _comidas(client, h_coach, r.json()["data"]["id"])[0]["subtitle"] is None


def test_se_puede_cambiar_y_se_puede_borrar(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear_dieta(client, h_coach, suf)
    comida = _comidas(client, h_coach, did)[0]

    def guardar(sub):
        r = client.put(f"/api/diets/{did}/update", headers=h_coach, json={
            "id": did, "title": f"Dieta {suf}",
            "foods": [{"id": comida["id"], "name": "Desayuno", "subtitle": sub,
                       "time": "08:00", "detail": []}]})
        assert r.status_code == 200, r.text
        return _comidas(client, h_coach, did)[0]["subtitle"]

    assert guardar("Tortilla francesa") == "Tortilla francesa"
    # Vacío SÍ borra: es lo que hace el coach al limpiar el recuadro.
    assert guardar("") is None


def test_UNA_EDICION_QUE_NO_LO_MANDA_NO_LO_BORRA(client, seed, admin_headers):
    """Cambiar solo la hora de una comida no puede llevarse por delante lo que
    el coach escribió, sin que nadie lo haya pedido."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear_dieta(client, h_coach, suf)
    comida = _comidas(client, h_coach, did)[0]

    r = client.put(f"/api/diets/{did}/update", headers=h_coach, json={
        "id": did, "title": f"Dieta {suf}",
        "foods": [{"id": comida["id"], "name": "Desayuno", "time": "09:30", "detail": []}]})
    assert r.status_code == 200, r.text

    de_nuevo = _comidas(client, h_coach, did)[0]
    assert de_nuevo["time"] == "09:30", de_nuevo
    assert de_nuevo["subtitle"] == "Huevos revueltos con aguacate", de_nuevo


def test_un_subtitulo_larguisimo_no_revienta_la_columna(client, seed, admin_headers):
    """La columna admite 255. Pegar un párrafo entero es raro pero pasa, y un
    error de base de datos ahí se lleva la dieta entera por delante."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear_dieta(client, h_coach, suf, subtitulo="x" * 600)
    assert len(_comidas(client, h_coach, did)[0]["subtitle"]) == 255


# ── Donde de verdad se pierde: la copia al cliente ─────────────────────────

def test_AL_ASIGNAR_LA_DIETA_EL_SUBTITULO_LLEGA_AL_CLIENTE(client, seed, admin_headers):
    """Es a quien va dirigido. Si la copia no se lo llevara, el coach lo vería
    en su biblioteca y su cliente no."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _crear_dieta(client, h_coach, suf)

    r = client.post(f"/api/diets/{did}/assign", headers=h_coach,
                    json={"client_id": det_cli})
    assert r.status_code == 200, r.text

    # Y se ve en su pantalla de nutrición, que es donde lo mira.
    datos = client.get("/api/client/nutrition", headers=h_cli).json()["data"]
    comidas = [m for d in datos["days"] for m in (d.get("meals") or [])]
    assert comidas, datos
    assert comidas[0]["subtitle"] == "Huevos revueltos con aguacate", comidas[0]


def test_la_copia_es_independiente_del_original(client, seed, admin_headers):
    """Cambiar la plantilla de la biblioteca no le cambia la comida a un
    cliente al que ya se le asignó."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _crear_dieta(client, h_coach, suf)
    client.post(f"/api/diets/{did}/assign", headers=h_coach, json={"client_id": det_cli})

    comida = _comidas(client, h_coach, did)[0]
    client.put(f"/api/diets/{did}/update", headers=h_coach, json={
        "id": did, "title": f"Dieta {suf}",
        "foods": [{"id": comida["id"], "name": "Desayuno", "subtitle": "Otra cosa",
                   "time": "08:00", "detail": []}]})

    datos = client.get("/api/client/nutrition", headers=h_cli).json()["data"]
    comidas = [m for d in datos["days"] for m in (d.get("meals") or [])]
    assert comidas[0]["subtitle"] == "Huevos revueltos con aguacate", comidas[0]


def test_el_pdf_se_genera_con_el_subtitulo_dentro(client, seed, admin_headers):
    """El cliente se lleva el PDF a la cocina: si el subtítulo solo estuviera
    en la app, ahí abajo pondría "Desayuno" y nada más."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _det, _hc = _monta(client, admin_headers, suf)
    did = _crear_dieta(client, h_coach, suf)

    r = client.get(f"/api/diets/{did}/pdf", headers=h_coach)
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF", r.content[:20]

    # Que el generador recibe el dato es lo que se puede comprobar sin
    # extraer texto del PDF: dentro va por el mismo camino que el nombre.
    db = SessionLocal()
    try:
        fila = db.query(DietFood).filter(DietFood.diet_id == did).first()
        assert fila.subtitle == "Huevos revueltos con aguacate", fila.subtitle
    finally:
        db.close()
