"""Progreso · Fuerza: el historial por ejercicio.

Cinco métricas del mismo levantamiento, y cada una con su forma de salir mal:

  · El 1RM se estima con Epley —peso × (1 + reps/30)—, que es la fórmula que
    cuadra con los números que ya maneja el cliente. Otra fórmula da otra
    cifra para el mismo levantamiento, y el coach compara con lo que tenía
    anotado.
  · El RIR no es un dato aparte: es 10 − RPE. El cliente marca RPE al
    entrenar y son dos formas de decir lo mismo.
  · El PESO TOP y las REPS que se enseñan son del MISMO levantamiento. Coger
    el peso de una serie y las repeticiones de otra da un 1RM que nadie hizo.
  · Y una plancha no tiene peso top. Enseñar "0 kg" le diría al coach que el
    cliente no levantó nada, cuando ahí no se levanta.
"""
import uuid
from datetime import date, timedelta

from app.core.entrenos import es_por_tiempo, mmss, rir_de_rpe, rm_estimado, segundos
from app.database import SessionLocal
from app.models.session_log import WorkoutSession, WorkoutSessionExercise, WorkoutSessionSet

from tests.test_org_scope import _crear_coach, _crear_usuario


def _monta(client, admin_headers, suf):
    _u, _d, h_coach = _crear_coach(client, admin_headers, f"coach.fz.{suf}@nutrientrena-qa.com")
    _uid, det_cli, _h = _crear_usuario(client, admin_headers, f"cli.fz.{suf}@nutrientrena-qa.com", role_id=6)
    return h_coach, det_cli


def _sesion(det_cli, dia, ejercicio, grupo, series, training_id=None):
    """`series` es [(reps, kg, hecha, rpe)]."""
    db = SessionLocal()
    try:
        s = WorkoutSession(client_user_detail_id=det_cli, session_date=dia)
        db.add(s); db.flush()
        ex = WorkoutSessionExercise(session_id=s.id, name=ejercicio,
                                    muscle_group_name=grupo, training_id=training_id)
        db.add(ex); db.flush()
        for i, (reps, kg, hecha, rpe) in enumerate(series, start=1):
            db.add(WorkoutSessionSet(session_exercise_id=ex.id, set_number=i,
                                     reps=reps, weight=kg, done=hecha, rpe=rpe))
        db.commit()
    finally:
        db.close()


def _fuerza(client, headers, det_cli):
    r = client.get(f"/api/session-logs/client/{det_cli}/fuerza", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]["ejercicios"]


# ── Las fórmulas, contra los números del propio cliente ────────────────────

def test_EL_1RM_ES_EL_QUE_YA_USA_EL_CLIENTE():
    """Las seis filas de su prototipo. Otra fórmula daría otras cifras para el
    mismo levantamiento y no cuadrarían con lo que tiene anotado."""
    assert rm_estimado(77.5, 6) == 93.0
    assert rm_estimado(75, 8) == 95.0
    assert rm_estimado(75, 6) == 90.0
    assert rm_estimado(72.5, 8) == 91.8
    assert rm_estimado(72.5, 6) == 87.0
    assert rm_estimado(70, 6) == 84.0


def test_una_serie_por_tiempo_no_tiene_1rm():
    assert rm_estimado(20, None) is None
    assert rm_estimado(None, 8) is None


def test_EL_RIR_SALE_DEL_RPE():
    """RIR = 10 − RPE. Un RPE de 8,5 son 1,5 repeticiones en recámara, que es
    el "RIR promedio" del prototipo."""
    assert rir_de_rpe(8.5) == 1.5
    assert rir_de_rpe(9) == 1.0
    assert rir_de_rpe(10) == 0.0
    assert rir_de_rpe(None) is None
    # Un RPE por encima de 10 no da repeticiones negativas.
    assert rir_de_rpe(11) == 0.0


def test_los_tiempos_se_leen_como_tiempos():
    assert segundos("40s") == 40
    assert segundos("1 min") == 60
    assert segundos("2 min") == 120
    assert mmss(135) == "2:15"
    assert mmss(60) == "1:00"
    assert mmss(None) is None


def test_un_ejercicio_es_de_tiempo_si_todas_sus_series_lo_son():
    class _S:
        def __init__(self, reps, done=True):
            self.reps, self.done = reps, done
    assert es_por_tiempo([_S("40s"), _S("45s")]) is True
    assert es_por_tiempo([_S("8"), _S("10")]) is False
    # Con una sola serie por repeticiones ya no es de tiempo.
    assert es_por_tiempo([_S("40s"), _S("8")]) is False
    assert es_por_tiempo([]) is False


# ── Por el camino real ─────────────────────────────────────────────────────

def test_EL_PESO_TOP_Y_SUS_REPS_SON_DEL_MISMO_LEVANTAMIENTO(client, seed, admin_headers):
    """Coger el peso de una serie y las repeticiones de otra da un 1RM que
    nadie hizo — y en fuerza esa cifra es la que se persigue."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), "Press banca", "Pecho", [
        ("12", 60.0, True, 7.0),     # muchas reps, poco peso
        ("6", 77.5, True, 8.5),      # la más pesada
    ])
    e = _fuerza(client, h_coach, det_cli)[0]
    f = e["sesiones"][0]
    assert f["peso_top"] == 77.5, f
    assert f["reps_top"] == 6, "ha cogido las repeticiones de otra serie"
    assert f["rm1"] == 93.0, f["rm1"]


def test_el_volumen_suma_todas_las_series_hechas(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), "Press banca", "Pecho", [
        ("6", 77.5, True, 8.0),      # 465
        ("6", 77.5, True, 8.0),      # 465
        ("6", 77.5, False, None),    # sin marcar: fuera
    ])
    f = _fuerza(client, h_coach, det_cli)[0]["sesiones"][0]
    assert f["volumen"] == 930.0, f["volumen"]
    assert f["series"] == 2, f["series"]


def test_UNA_PLANCHA_NO_TIENE_PESO_TOP(client, seed, admin_headers):
    """Enseñar "0 kg" le diría al coach que no levantó nada, y ahí no se
    levanta: se mide en segundos."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), "Plancha abdominal", "Core", [
        ("60s", None, True, 7.0), ("135s", None, True, 8.0)])
    e = _fuerza(client, h_coach, det_cli)[0]
    assert e["tipo"] == "tiempo", e["tipo"]
    assert e["pr_peso"] is None and e["rm1_max"] is None
    assert e["sesiones"][0]["tiempo"] == "2:15", e["sesiones"][0]


def test_el_rir_de_la_sesion_es_la_media_de_sus_series(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), "Press banca", "Pecho", [
        ("6", 70.0, True, 8.0), ("6", 70.0, True, 9.0)])   # RPE medio 8.5
    f = _fuerza(client, h_coach, det_cli)[0]["sesiones"][0]
    assert f["rir"] == 1.5, f["rir"]


def test_las_sesiones_van_de_la_mas_vieja_a_la_mas_nueva(client, seed, admin_headers):
    """El gráfico se dibuja en ese orden. Al revés, la línea de progreso baja
    cuando el cliente ha subido."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    for i, kg in enumerate([70.0, 72.5, 77.5]):
        _sesion(det_cli, date.today() - timedelta(days=14 - i * 7),
                "Press banca", "Pecho", [("6", kg, True, 8.0)])
    fs = _fuerza(client, h_coach, det_cli)[0]["sesiones"]
    assert [f["peso_top"] for f in fs] == [70.0, 72.5, 77.5], fs


def test_los_records_son_el_maximo_historico(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today() - timedelta(days=7), "Press banca", "Pecho",
            [("6", 80.0, True, 9.0)])                      # el récord fue antes
    _sesion(det_cli, date.today(), "Press banca", "Pecho",
            [("6", 75.0, True, 8.0)])
    e = _fuerza(client, h_coach, det_cli)[0]
    assert e["pr_peso"] == 80.0, "el récord no es el último, es el mayor"
    assert e["volumen_ultimo"] == 450.0, "el volumen SÍ es el de la última"


def test_una_sesion_sin_series_marcadas_no_cuenta(client, seed, admin_headers):
    """Empezar el entreno y no marcar nada no es haber entrenado ese ejercicio."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), "Press banca", "Pecho", [("6", 70.0, False, None)])
    assert _fuerza(client, h_coach, det_cli) == []


def test_los_mas_entrenados_salen_primero(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    for i in range(3):
        _sesion(det_cli, date.today() - timedelta(days=i), "Press banca", "Pecho",
                [("6", 70.0, True, 8.0)])
    _sesion(det_cli, date.today(), "Curl", "Bíceps", [("10", 20.0, True, 7.0)])
    nombres = [e["nombre"] for e in _fuerza(client, h_coach, det_cli)]
    assert nombres[0] == "Press banca", nombres


def test_un_cliente_no_ve_la_fuerza_de_otro(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _h, det_cli = _monta(client, admin_headers, suf)
    _uid, _d, h_otro = _crear_usuario(
        client, admin_headers, f"cli.fisgon.fz.{suf}@nutrientrena-qa.com", role_id=6)
    r = client.get(f"/api/session-logs/client/{det_cli}/fuerza", headers=h_otro)
    assert r.status_code == 403, r.status_code
