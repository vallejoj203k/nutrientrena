"""La agenda que enseña el Inicio del coach.

El panel de "Próximos 5 días" pedía sus eventos a `/api/events`, una ruta que
no existe: devolvía 405 y la agenda salía siempre vacía, con cinco "Sin
eventos" dijera lo que dijera el calendario. La ruta buena es
`/api/events/search`, con su ventana de fechas.

Lo que hay que dejar sujeto:

  · Que exista y devuelva los eventos de esa ventana, y solo esos.
  · Que traiga lo que el panel necesita para pintar la fila: el título, la
    fecha y el TIPO con su color.
  · Que un coach no vea la agenda de otro.
"""
import uuid
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.type_event import TypeEvent

from tests.test_macros_porcion import _monta


def _tipo(nombre, color):
    db = SessionLocal()
    try:
        t = db.query(TypeEvent).filter(TypeEvent.name == nombre).first()
        if not t:
            t = TypeEvent(name=nombre, color=color, state=1)
            db.add(t)
            db.commit()
        return t.id
    finally:
        db.close()


def _crear(client, h, titulo, cuando, tipo_id=None, **extra):
    body = {"title": titulo, "start_date": cuando.isoformat()}
    if tipo_id:
        body["type_event_id"] = tipo_id
    body.update(extra)
    r = client.post("/api/events", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _ventana(client, h, desde, hasta):
    r = client.get(f"/api/events/search?start={desde.isoformat()}&end={hasta.isoformat()}",
                   headers=h)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_LA_AGENDA_DE_LOS_PROXIMOS_DIAS_LLEGA(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    ahora = datetime(2026, 5, 15, 9, 0)
    _crear(client, h, f"Sesión online {suf}", ahora + timedelta(days=3))

    hallados = _ventana(client, h, ahora, ahora + timedelta(days=5))
    assert any(e["title"] == f"Sesión online {suf}" for e in hallados), hallados


def test_lo_que_cae_fuera_de_la_ventana_no_entra(client, seed, admin_headers):
    """El panel enseña cinco días: uno de la semana que viene no pinta nada
    ahí, y colarlo desplazaría a los que sí."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    ahora = datetime(2026, 5, 15, 9, 0)
    _crear(client, h, f"Dentro {suf}", ahora + timedelta(days=2))
    _crear(client, h, f"La semana que viene {suf}", ahora + timedelta(days=9))
    _crear(client, h, f"Ayer {suf}", ahora - timedelta(days=1))

    titulos = [e["title"] for e in _ventana(client, h, ahora, ahora + timedelta(days=5))]
    assert f"Dentro {suf}" in titulos, titulos
    assert f"La semana que viene {suf}" not in titulos, titulos
    assert f"Ayer {suf}" not in titulos, titulos


def test_TRAE_EL_TIPO_CON_SU_COLOR(client, seed, admin_headers):
    """El punto de cada fila se pinta con el color de su tipo, el mismo que
    usa el calendario. Sin el tipo, todos saldrían grises."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    tipo = _tipo("Cita", "#3B82F6")
    ahora = datetime(2026, 5, 15, 9, 0)
    _crear(client, h, f"Con tipo {suf}", ahora + timedelta(days=1), tipo_id=tipo)

    e = [x for x in _ventana(client, h, ahora, ahora + timedelta(days=5))
         if x["title"] == f"Con tipo {suf}"][0]
    assert e["type_event"], e
    assert e["type_event"]["color"] == "#3B82F6", e["type_event"]


def test_trae_la_hora_y_si_es_de_todo_el_dia(client, seed, admin_headers):
    """Un evento de todo el día no tiene hora que enseñar; uno con hora, sí."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    ahora = datetime(2026, 5, 15, 9, 0)
    _crear(client, h, f"Todo el día {suf}", datetime(2026, 5, 16, 0, 0), all_day=1)
    _crear(client, h, f"A las diez {suf}", datetime(2026, 5, 17, 10, 0))

    por = {e["title"]: e for e in _ventana(client, h, ahora, ahora + timedelta(days=5))}
    assert por[f"Todo el día {suf}"]["all_day"] == 1
    assert por[f"A las diez {suf}"]["all_day"] == 0
    assert por[f"A las diez {suf}"]["start_date"].startswith("2026-05-17T10:00")


def test_vienen_ordenados_por_fecha(client, seed, admin_headers):
    """El panel los reparte por día, pero dentro de un día manda la hora."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    ahora = datetime(2026, 5, 15, 9, 0)
    _crear(client, h, f"Tarde {suf}", datetime(2026, 5, 16, 18, 0))
    _crear(client, h, f"Mañana {suf}", datetime(2026, 5, 16, 9, 0))

    titulos = [e["title"] for e in _ventana(client, h, ahora, ahora + timedelta(days=5))
               if e["title"].endswith(suf)]
    assert titulos == [f"Mañana {suf}", f"Tarde {suf}"], titulos


def test_UN_COACH_NO_VE_LA_AGENDA_DE_OTRO(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_mio, _d1, _h1 = _monta(client, admin_headers, f"{suf}a")
    h_otro, _d2, _h2 = _monta(client, admin_headers, f"{suf}b")
    ahora = datetime(2026, 5, 15, 9, 0)
    _crear(client, h_mio, f"Mi sesión {suf}", ahora + timedelta(days=1))

    titulos = [e["title"] for e in _ventana(client, h_otro, ahora, ahora + timedelta(days=5))]
    assert f"Mi sesión {suf}" not in titulos, titulos


def test_una_agenda_vacia_devuelve_una_lista_vacia(client, seed, admin_headers):
    """Y no un error: el panel enseña los cinco días con "Sin eventos"."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    ahora = datetime(2026, 5, 15, 9, 0)
    assert _ventana(client, h, ahora, ahora + timedelta(days=5)) == []
