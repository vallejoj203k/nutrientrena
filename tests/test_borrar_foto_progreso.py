"""Deshacer una foto de progreso subida por error.

No había vuelta atrás, y no por descuido: el `POST /client/checkin` solo
escribe los campos que LLEGAN —para que mandar solo el peso no borre las
medidas—, así que enviar la foto vacía no la borraba, la ignoraba. Una foto
equivocada se quedaba en el progreso del cliente y en la bandeja del coach
para siempre.

Lo que hay que vigilar al borrarla:

  · que un cliente no pueda borrar las fotos de otro cambiando el número de la
    URL;
  · que las otras fotos y el peso del mismo check-in no se vayan por delante;
  · que un check-in que existía SOLO para llevar esa foto no se quede en el
    historial como una fila en blanco;
  · y que la tarea del calendario que se dio por hecha gracias a esa foto
    vuelva a estar pendiente. Dejarla en verde le diría al cliente que no
    tiene nada que enviar cuando sí lo tiene.
"""
import uuid
from datetime import date

from app.database import SessionLocal
from app.models.checkin import WeeklyCheckin
from app.models.user import UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario

FOTO = "https://cdn.ejemplo.test/progress/una-foto.jpg"
OTRA = "https://cdn.ejemplo.test/progress/otra-foto.jpg"


def _monta(client, admin_headers, suf, quien="a"):
    _uid, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.foto.{quien}.{suf}@nutrientrena-qa.com")
    _u2, det_cli, h_cli = _crear_usuario(
        client, admin_headers, f"cli.foto.{quien}.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        db.commit()
    finally:
        db.close()
    return h_coach, det_cli, h_cli


def _fotos(client, h_cli):
    r = client.get("/api/client/progress", headers=h_cli)
    assert r.status_code == 200, r.text
    return r.json()["data"]["photos"]


def _checkins(det_cli):
    db = SessionLocal()
    try:
        return db.query(WeeklyCheckin).filter(
            WeeklyCheckin.client_user_detail_id == det_cli).all()
    finally:
        db.close()


# ── Lo básico ──────────────────────────────────────────────────────────────

def test_LA_FOTO_SE_PUEDE_BORRAR(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _h_coach, _det, h_cli = _monta(client, admin_headers, suf)
    client.post("/api/client/checkin", headers=h_cli, json={"photo_frontal": FOTO})

    ph = _fotos(client, h_cli)
    assert len(ph["frontal"]) == 1, ph
    ck_id = ph["frontal"][0]["id"]

    r = client.delete(f"/api/client/checkin/{ck_id}/foto/frontal", headers=h_cli)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["borrada"] is True

    assert _fotos(client, h_cli)["frontal"] == [], "la foto sigue saliendo en el progreso"


def test_la_pantalla_recibe_el_id_para_poder_borrarla(client, seed, admin_headers):
    """Sin el id, la pantalla tiene la imagen pero no sabe a quién pedirle que
    la borre. Es lo que faltaba en la respuesta."""
    suf = uuid.uuid4().hex[:8]
    _h, _d, h_cli = _monta(client, admin_headers, suf)
    client.post("/api/client/checkin", headers=h_cli, json={"photo_lateral": FOTO})
    assert _fotos(client, h_cli)["lateral"][0].get("id") is not None


def test_los_tres_angulos_se_borran_por_separado(client, seed, admin_headers):
    """Las tres viven en el mismo check-in. Borrar una no puede llevarse las
    otras: el cliente se equivocó en una foto, no en la sesión entera."""
    suf = uuid.uuid4().hex[:8]
    _h, _d, h_cli = _monta(client, admin_headers, suf)
    client.post("/api/client/checkin", headers=h_cli, json={
        "photo_frontal": FOTO, "photo_lateral": OTRA, "photo_espalda": FOTO})
    ck_id = _fotos(client, h_cli)["frontal"][0]["id"]

    client.delete(f"/api/client/checkin/{ck_id}/foto/lateral", headers=h_cli)
    ph = _fotos(client, h_cli)
    assert ph["lateral"] == [], "no se ha borrado la que se pidió"
    assert len(ph["frontal"]) == 1, "se ha llevado por delante la frontal"
    assert len(ph["espalda"]) == 1, "se ha llevado por delante la de espalda"


def test_un_angulo_que_no_existe_no_borra_nada(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _h, _d, h_cli = _monta(client, admin_headers, suf)
    client.post("/api/client/checkin", headers=h_cli, json={"photo_frontal": FOTO})
    ck_id = _fotos(client, h_cli)["frontal"][0]["id"]

    r = client.delete(f"/api/client/checkin/{ck_id}/foto/perfil", headers=h_cli)
    assert r.status_code == 400, r.text
    assert len(_fotos(client, h_cli)["frontal"]) == 1


def test_borrar_dos_veces_no_da_error(client, seed, admin_headers):
    """Un doble clic en el móvil no es un fallo del cliente."""
    suf = uuid.uuid4().hex[:8]
    _h, _d, h_cli = _monta(client, admin_headers, suf)
    client.post("/api/client/checkin", headers=h_cli, json={
        "weight": 70, "photo_frontal": FOTO})
    ck_id = _fotos(client, h_cli)["frontal"][0]["id"]

    assert client.delete(f"/api/client/checkin/{ck_id}/foto/frontal", headers=h_cli).status_code == 200
    r = client.delete(f"/api/client/checkin/{ck_id}/foto/frontal", headers=h_cli)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["borrada"] is False


# ── De quién es cada foto ──────────────────────────────────────────────────

def test_UN_CLIENTE_NO_BORRA_LAS_FOTOS_DE_OTRO(client, seed, admin_headers):
    """El id va en la URL. Sin comprobar de quién es el check-in, bastaría con
    cambiar el número para borrarle las fotos a cualquiera."""
    suf = uuid.uuid4().hex[:8]
    _h1, _d1, h_ana = _monta(client, admin_headers, suf, "ana")
    _h2, _d2, h_luis = _monta(client, admin_headers, suf, "luis")

    client.post("/api/client/checkin", headers=h_ana, json={"photo_frontal": FOTO})
    ck_de_ana = _fotos(client, h_ana)["frontal"][0]["id"]

    r = client.delete(f"/api/client/checkin/{ck_de_ana}/foto/frontal", headers=h_luis)
    assert r.status_code == 404, r.text
    assert len(_fotos(client, h_ana)["frontal"]) == 1, "le han borrado la foto a otra persona"


# ── Lo que queda detrás ────────────────────────────────────────────────────

def test_EL_CHECKIN_VACIO_NO_SE_QUEDA_EN_EL_HISTORIAL(client, seed, admin_headers):
    """Subir una foto crea un check-in. Si el cliente la sube por error y la
    quita, ese check-in no tiene nada dentro: dejarlo pondría una fila en
    blanco en su historial y en la bandeja del coach."""
    suf = uuid.uuid4().hex[:8]
    _h, det_cli, h_cli = _monta(client, admin_headers, suf)
    client.post("/api/client/checkin", headers=h_cli, json={"photo_frontal": FOTO})
    assert len(_checkins(det_cli)) == 1

    ck_id = _fotos(client, h_cli)["frontal"][0]["id"]
    r = client.delete(f"/api/client/checkin/{ck_id}/foto/frontal", headers=h_cli)
    assert r.json()["data"]["checkin_borrado"] is True
    assert _checkins(det_cli) == [], "queda un check-in en blanco"


def test_pero_no_se_borra_el_checkin_que_tenia_mas_cosas(client, seed, admin_headers):
    """Aquí el cliente pesó, contó cómo fue la semana y además subió la foto.
    Quitar la foto no puede llevarse el check-in: perdería el peso."""
    suf = uuid.uuid4().hex[:8]
    _h, det_cli, h_cli = _monta(client, admin_headers, suf)
    client.post("/api/client/checkin", headers=h_cli, json={
        "weight": 70.5, "energy": 8, "photo_frontal": FOTO})

    ck_id = _fotos(client, h_cli)["frontal"][0]["id"]
    r = client.delete(f"/api/client/checkin/{ck_id}/foto/frontal", headers=h_cli)
    assert r.json()["data"]["checkin_borrado"] is False

    quedan = _checkins(det_cli)
    assert len(quedan) == 1, "se ha borrado un check-in con datos"
    assert quedan[0].weight == 70.5, "se ha perdido el peso"
    assert quedan[0].energy == 8


def test_LA_TAREA_QUE_PEDIA_LA_FOTO_VUELVE_A_ESTAR_PENDIENTE(client, seed, admin_headers):
    """La tarea se marcó sola porque llegó la foto. Si la foto se va, la tarea
    no está cumplida, y dejarla en verde le diría al cliente que no tiene nada
    pendiente cuando sí lo tiene."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    r = client.post("/api/calendar-tasks", headers=h_coach, json={
        "client_user_detail_id": det_cli,
        "task_date": date.today().isoformat(),
        "task_type": "checkin",
        "title": "Manda tus fotos",
        "requirements": {"items": ["fotos"]},
    })
    assert r.status_code == 200, r.text
    tarea = r.json()["data"]["id"]

    client.post("/api/client/checkin", headers=h_cli, json={"photo_frontal": FOTO})
    espera = client.get("/api/checkins/bandeja", headers=h_coach).json()["data"]["esperando"]
    assert espera == [], "la tarea no llegó a marcarse; la prueba no comprueba nada"

    ck_id = _fotos(client, h_cli)["frontal"][0]["id"]
    client.delete(f"/api/client/checkin/{ck_id}/foto/frontal", headers=h_cli)

    espera = client.get("/api/checkins/bandeja", headers=h_coach).json()["data"]["esperando"]
    assert [t["task_id"] for t in espera] == [tarea], \
        "la tarea sigue dada por hecha sin la foto que la cumplía"


def test_la_tarea_de_peso_no_se_desmarca_por_quitar_una_foto(client, seed, admin_headers):
    """Solo deja de estar hecha la tarea que dependía de lo que se ha quitado.
    Desmarcarlas todas sería devolverle al cliente trabajo que ya hizo."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    client.post("/api/calendar-tasks", headers=h_coach, json={
        "client_user_detail_id": det_cli,
        "task_date": date.today().isoformat(),
        "task_type": "checkin",
        "title": "Pésate",
        "requirements": {"items": ["peso"]},
    })
    client.post("/api/client/checkin", headers=h_cli, json={"weight": 70.5, "photo_frontal": FOTO})
    assert client.get("/api/checkins/bandeja", headers=h_coach).json()["data"]["esperando"] == []

    ck_id = _fotos(client, h_cli)["frontal"][0]["id"]
    client.delete(f"/api/client/checkin/{ck_id}/foto/frontal", headers=h_cli)

    espera = client.get("/api/checkins/bandeja", headers=h_coach).json()["data"]["esperando"]
    assert espera == [], "se ha desmarcado una tarea de peso por quitar una foto"
