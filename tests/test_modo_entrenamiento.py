"""Los dos modos de programar el entrenamiento de un cliente.

El espejo de lo que ya existía para la nutrición: un plan semanal que se
repite, o el calendario día a día.

Lo que hay que dejar sujeto:

  · Que sea SUYO. Nutrición y entrenamiento se guardan por separado, porque un
    coach puede tener la comida cerrada en un plan fijo y los entrenos día a
    día. Si compartieran interruptor, tocar uno cambiaría el otro sin avisar.
  · Que la pausa NO borre. Volver al plan semanal tiene que devolver la rutina
    que había: es lo que promete la ventana de confirmación.
  · Que un modo mal escrito se rechace. Guardar "calendarío" dejaría al cliente
    sin plan de ninguno de los dos tipos, y eso no se nota hasta que pregunta.
  · Y de quién es cada cliente: el modo se cambia por el id que va en la URL.
"""
import uuid

from app.database import SessionLocal
from app.models.user import UserDetail

from tests.test_nutricion_cliente import _monta


def _modo_ent(client, headers, det_cli, modo):
    return client.put(f"/api/users/client/{det_cli}/training-mode",
                      headers=headers, json={"training_mode": modo})


def _modo_nut(client, headers, det_cli, modo):
    return client.put(f"/api/users/client/{det_cli}/nutrition-mode",
                      headers=headers, json={"nutrition_mode": modo})


def _guardado(det_cli):
    db = SessionLocal()
    try:
        d = db.query(UserDetail).filter(UserDetail.id == det_cli).first()
        return (d.training_mode, d.nutrition_mode)
    finally:
        db.close()


# ── Lo básico ──────────────────────────────────────────────────────────────

def test_el_modo_de_entrenamiento_se_guarda(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h_cli = _monta(client, admin_headers, suf)

    r = _modo_ent(client, h_coach, det_cli, "calendario")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["training_mode"] == "calendario"
    assert _guardado(det_cli)[0] == "calendario"

    _modo_ent(client, h_coach, det_cli, "semanal")
    assert _guardado(det_cli)[0] == "semanal"


def test_por_defecto_es_el_plan_semanal(client, seed, admin_headers):
    """Un cliente nuevo no puede aparecer "en calendario" sin que nadie lo haya
    puesto: el coach vería su rutina en pausa sin haber tocado nada."""
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h = _monta(client, admin_headers, suf)
    r = client.get(f"/api/users/{det_cli}/edit", headers=h_coach)
    assert r.status_code == 200, r.text
    assert (r.json()["data"].get("training_mode") or "semanal") == "semanal"


def test_LA_PANTALLA_RECIBE_EL_MODO(client, seed, admin_headers):
    """La ficha del cliente lo necesita para saber qué modo pintar como activo.
    Sin él en la respuesta, el selector se abre siempre en "semanal" y el coach
    ve un modo que no es el que tiene puesto."""
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h = _monta(client, admin_headers, suf)
    _modo_ent(client, h_coach, det_cli, "calendario")

    # La ficha se carga con `/users/{id}/edit`, que es de donde sale `clientData`.
    datos = client.get(f"/api/users/{det_cli}/edit", headers=h_coach).json()["data"]
    assert datos.get("training_mode") == "calendario", datos.get("training_mode")


# ── Son dos decisiones distintas ───────────────────────────────────────────

def test_EL_ENTRENAMIENTO_Y_LA_NUTRICION_VAN_POR_SEPARADO(client, seed, admin_headers):
    """Un coach puede tener la comida cerrada en un plan fijo y los entrenos
    día a día. Con un solo interruptor tendría que llevarlas igual, y peor:
    cambiar una le cambiaría la otra sin decírselo."""
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h = _monta(client, admin_headers, suf)

    _modo_ent(client, h_coach, det_cli, "calendario")
    assert _guardado(det_cli) == ("calendario", "semanal"), \
        "cambiar el entrenamiento ha movido la nutrición"

    _modo_nut(client, h_coach, det_cli, "calendario")
    assert _guardado(det_cli) == ("calendario", "calendario")

    _modo_nut(client, h_coach, det_cli, "semanal")
    assert _guardado(det_cli) == ("calendario", "semanal"), \
        "volver la nutrición al plan semanal ha arrastrado el entrenamiento"


# ── Lo que no puede pasar ──────────────────────────────────────────────────

def test_UN_MODO_QUE_NO_EXISTE_SE_RECHAZA(client, seed, admin_headers):
    """Guardar cualquier cosa dejaría al cliente sin plan de ninguno de los dos
    tipos, y eso no da error: simplemente no se ve nada."""
    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h = _monta(client, admin_headers, suf)

    for malo in ("calendarío", "CALENDARIO ", "diario", ""):
        r = _modo_ent(client, h_coach, det_cli, malo)
        if malo == "CALENDARIO ":
            # Espacios y mayúsculas sí se perdonan: es la misma palabra.
            assert r.status_code == 200, r.text
            assert _guardado(det_cli)[0] == "calendario"
            continue
        assert r.status_code == 400, f"{malo!r} -> {r.status_code} {r.text}"

    # Y después de todos los intentos, sigue en un modo válido.
    assert _guardado(det_cli)[0] in ("semanal", "calendario")


def test_la_pausa_no_borra_la_rutina(client, seed, admin_headers):
    """Es lo que promete la ventana: "el otro modo queda en pausa, no se
    borra". Cambiar de modo solo puede tocar la columna del modo."""
    from app.models.routine import Routine
    from app.models.user import UserDetail as UD

    suf = uuid.uuid4().hex[:8]
    _det_coach, h_coach, det_cli, _h = _monta(client, admin_headers, suf)

    db = SessionLocal()
    try:
        det = db.query(UD).filter(UD.id == det_cli).first()
        db.add(Routine(name=f"Fuerza {suf}", user_id=det.user_id))
        db.commit()
        antes = db.query(Routine).filter(Routine.user_id == det.user_id).count()
    finally:
        db.close()
    assert antes == 1

    _modo_ent(client, h_coach, det_cli, "calendario")
    _modo_ent(client, h_coach, det_cli, "semanal")

    db = SessionLocal()
    try:
        det = db.query(UD).filter(UD.id == det_cli).first()
        assert db.query(Routine).filter(
            Routine.user_id == det.user_id).count() == antes, "la rutina ha desaparecido"
    finally:
        db.close()


def test_UN_COACH_NO_CAMBIA_EL_MODO_DE_UN_CLIENTE_AJENO(client, seed, admin_headers):
    """El id del cliente va en la URL: sin comprobar de quién es, cualquier
    coach podría poner en pausa la rutina de un cliente de otro."""
    suf = uuid.uuid4().hex[:8]
    _dc1, _h_mio, det_mio, _h1 = _monta(client, admin_headers, suf + "a")
    _dc2, h_otro, _det_otro, _h2 = _monta(client, admin_headers, suf + "b")

    r = _modo_ent(client, h_otro, det_mio, "calendario")
    assert r.status_code in (403, 404), r.status_code
    assert _guardado(det_mio)[0] in (None, "semanal"), \
        "le han cambiado el modo a un cliente de otro coach"
