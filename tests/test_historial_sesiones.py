"""El historial de sesiones que ve el coach en Progreso.

Son cuentas, y cada una tiene una forma obvia de salir mal:

  · El TONELAJE se calcula sobre las series HECHAS. Contar las que el cliente
    dejó a medias diría que levantó lo que no levantó, y precisamente en las
    sesiones parciales, que es donde el coach mira.
  · Una serie de "40s" no son 40 repeticiones. Colada en el tonelaje, una
    plancha de 40 segundos con 20 kg suma 800 kg de una sentada.
  · Una sesión SALTADA no existe en la base: es un día que el coach programó en
    el calendario y el cliente no registró. Se construye al leer.
  · Y la ADHERENCIA sin nada programado no es 100%: es que no hay nada que
    medir. Un 100% con cero sesiones es una nota excelente por no hacer nada.
"""
import json
import uuid
from datetime import date, datetime, timedelta

from app.core.entrenos import estado, racha_semanas, repeticiones, semana_del_programa
from app.database import SessionLocal
from app.models.calendar_task import CalendarTask
from app.models.session_log import WorkoutSession, WorkoutSessionExercise, WorkoutSessionSet
from app.models.user import UserDetail

from tests.test_org_scope import _crear_coach, _crear_usuario


def _lunes(delta_semanas=0):
    hoy = date.today()
    return hoy - timedelta(days=hoy.weekday()) - timedelta(days=7 * delta_semanas)


def _monta(client, admin_headers, suf, inicio=None):
    _u, _det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.hist.{suf}@nutrientrena-qa.com")
    _uid, det_cli, _h = _crear_usuario(
        client, admin_headers, f"cli.hist.{suf}@nutrientrena-qa.com", role_id=6)
    if inicio:
        db = SessionLocal()
        try:
            d = db.query(UserDetail).filter(UserDetail.id == det_cli).first()
            d.start_date = datetime.combine(inicio, datetime.min.time())
            db.commit()
        finally:
            db.close()
    return h_coach, det_cli


def _sesion(det_cli, dia, series, duracion=40, rpe=8.0, mood=None):
    """`series` es [(reps, kg, hecha)]."""
    db = SessionLocal()
    try:
        s = WorkoutSession(client_user_detail_id=det_cli, session_date=dia,
                           duration_min=duracion, rpe=rpe, mood=mood)
        db.add(s)
        db.flush()
        ex = WorkoutSessionExercise(session_id=s.id, name="Press", muscle_group_name="Pecho")
        db.add(ex)
        db.flush()
        for i, (reps, kg, hecha) in enumerate(series, start=1):
            db.add(WorkoutSessionSet(session_exercise_id=ex.id, set_number=i,
                                     reps=reps, weight=kg, done=hecha))
        db.commit()
        return s.id
    finally:
        db.close()


def _programar(det_cli, coach_user_id, dia, titulo="Día 1"):
    db = SessionLocal()
    try:
        db.add(CalendarTask(client_user_detail_id=det_cli, coach_user_id=coach_user_id,
                            task_date=dia, task_type="rutina", title=titulo,
                            requirements=json.dumps({})))
        db.commit()
    finally:
        db.close()


def _historial(client, headers, det_cli):
    r = client.get(f"/api/session-logs/client/{det_cli}/historial", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ── Las repeticiones, que es de donde sale el tonelaje ─────────────────────

def test_UNA_SERIE_POR_TIEMPO_NO_SON_REPETICIONES():
    """"40s" leído como 40 repeticiones convierte una plancha en 800 kg."""
    assert repeticiones("40s") is None
    assert repeticiones("30 seg") is None
    assert repeticiones("1 min") is None
    assert repeticiones("8") == 8
    assert repeticiones("12 reps") == 12


def test_de_un_rango_se_coge_el_primero():
    """"8-10" son al menos 8. Quedarse con el 10 infla el tonelaje del cliente
    en cada serie de todo el programa."""
    assert repeticiones("8-10") == 8


def test_una_serie_sin_numero_no_aporta():
    assert repeticiones("") is None
    assert repeticiones("hasta el fallo") is None


# ── El estado ──────────────────────────────────────────────────────────────

def test_el_estado_de_una_sesion():
    assert estado(13, 13) == "completada"
    assert estado(11, 13) == "parcial"
    assert estado(0, 13) == "saltada"
    # Sin saber cuántas se preveían, haber marcado algo es haberla hecho.
    assert estado(5, 0) == "completada"
    assert estado(0, 0) == "saltada"


# ── El tonelaje, por el camino real ────────────────────────────────────────

def test_EL_TONELAJE_SOLO_CUENTA_LAS_SERIES_HECHAS(client, seed, admin_headers):
    """Contar las que dejó a medias diría que levantó lo que no levantó."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), [
        ("10", 50.0, True),      # 500
        ("10", 50.0, True),      # 500
        ("10", 50.0, False),     # no hecha: no cuenta
    ])
    fila = _historial(client, h_coach, det_cli)["sesiones"][0]
    assert fila["tonelaje"] == 1000.0, fila["tonelaje"]
    assert fila["series_hechas"] == 2 and fila["series_previstas"] == 3
    assert fila["estado"] == "parcial", fila["estado"]


def test_una_serie_por_tiempo_no_infla_el_tonelaje(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), [("40s", 20.0, True), ("10", 50.0, True)])
    fila = _historial(client, h_coach, det_cli)["sesiones"][0]
    assert fila["tonelaje"] == 500.0, fila["tonelaje"]


# ── Las saltadas, que no existen en la base ────────────────────────────────

def test_UN_DIA_PROGRAMADO_SIN_SESION_SALE_COMO_SALTADA(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    db = SessionLocal()
    try:
        coach_uid = db.query(UserDetail).filter(UserDetail.id == det_cli).first().user_id
    finally:
        db.close()

    ayer = date.today() - timedelta(days=1)
    _sesion(det_cli, date.today(), [("10", 50.0, True)])
    _programar(det_cli, coach_uid, date.today())     # esta sí se hizo
    _programar(det_cli, coach_uid, ayer)             # esta no

    datos = _historial(client, h_coach, det_cli)
    por_fecha = {f["fecha"]: f for f in datos["sesiones"]}
    assert por_fecha[ayer.isoformat()]["estado"] == "saltada"
    assert por_fecha[date.today().isoformat()]["estado"] != "saltada"
    # Y el día que sí se entrenó no se cuenta DOS veces.
    assert len(datos["sesiones"]) == 2, datos["sesiones"]
    assert datos["resumen"]["sesiones"] == 1
    assert datos["resumen"]["programadas"] == 2
    assert datos["resumen"]["saltadas"] == 1
    assert datos["resumen"]["adherencia"] == 50


def test_LO_PROGRAMADO_PARA_MANANA_NO_ESTA_SALTADO(client, seed, admin_headers):
    """Lo que aún no ha llegado no se ha saltado nadie. Contarlo hundiría la
    adherencia de todo cliente con el mes ya planificado."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    db = SessionLocal()
    try:
        coach_uid = db.query(UserDetail).filter(UserDetail.id == det_cli).first().user_id
    finally:
        db.close()

    _sesion(det_cli, date.today(), [("10", 50.0, True)])
    for i in range(1, 15):
        _programar(det_cli, coach_uid, date.today() + timedelta(days=i))

    datos = _historial(client, h_coach, det_cli)
    assert datos["resumen"]["saltadas"] == 0, datos["resumen"]
    assert datos["resumen"]["adherencia"] == 100


def test_sin_nada_programado_la_adherencia_no_es_cien(client, seed, admin_headers):
    """Un 100% con cero sesiones es una nota excelente por no hacer nada."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    datos = _historial(client, h_coach, det_cli)
    assert datos["resumen"]["adherencia"] is None, datos["resumen"]
    assert datos["resumen"]["sesiones"] == 0


# ── Las semanas del programa ───────────────────────────────────────────────

def test_la_semana_del_programa_empieza_en_uno():
    inicio = date(2026, 1, 5)
    assert semana_del_programa(inicio, inicio) == 1
    assert semana_del_programa(inicio + timedelta(days=6), inicio) == 1
    assert semana_del_programa(inicio + timedelta(days=7), inicio) == 2
    # Antes de empezar no hay semana que contar.
    assert semana_del_programa(inicio - timedelta(days=1), inicio) is None
    assert semana_del_programa(inicio, None) is None


def test_SIN_FECHA_DE_INICIO_NO_SE_INVENTA_LA_SEMANA(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)      # sin start_date
    _sesion(det_cli, date.today(), [("10", 50.0, True)])
    datos = _historial(client, h_coach, det_cli)
    assert datos["sesiones"][0]["semana"] is None
    assert datos["volumen_semanal"] == []


def test_el_volumen_por_semana_reparte_bien(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    inicio = _lunes(2)
    h_coach, det_cli = _monta(client, admin_headers, suf, inicio=inicio)
    _sesion(det_cli, inicio, [("10", 100.0, True)])                     # sem 1
    _sesion(det_cli, inicio + timedelta(days=8), [("10", 50.0, True)])  # sem 2

    datos = _historial(client, h_coach, det_cli)
    por_semana = {v["semana"]: v["tonelaje"] for v in datos["volumen_semanal"]}
    assert por_semana[1] == 1000.0, por_semana
    assert por_semana[2] == 500.0, por_semana


# ── La racha ───────────────────────────────────────────────────────────────

def test_la_racha_cuenta_semanas_seguidas():
    hoy = date(2026, 8, 27)          # jueves
    lunes = date(2026, 8, 24)
    tres = [lunes, lunes - timedelta(days=7), lunes - timedelta(days=14)]
    assert racha_semanas(tres, hoy=hoy) == 3


def test_LA_SEMANA_EN_CURSO_NO_ROMPE_LA_RACHA():
    """Es jueves y aún no ha entrenado esta semana: la racha de las anteriores
    sigue viva. Ponerla a cero castigaría por un día que aún no ha pasado."""
    hoy = date(2026, 8, 27)
    anteriores = [date(2026, 8, 17), date(2026, 8, 10)]
    assert racha_semanas(anteriores, hoy=hoy) == 2


def test_un_hueco_rompe_la_racha():
    hoy = date(2026, 8, 27)
    con_hueco = [date(2026, 8, 24), date(2026, 8, 3)]
    assert racha_semanas(con_hueco, hoy=hoy) == 1


def test_sin_entrenos_no_hay_racha():
    assert racha_semanas([]) == 0


# ── El ánimo ───────────────────────────────────────────────────────────────

def test_EL_ANIMO_VACIO_NO_SE_RELLENA(client, seed, admin_headers):
    """Las sesiones de antes no lo tienen, y las de ahora tampoco si el cliente
    prefiere no decirlo. Un "normal" por defecto sería un dato que nadie dio."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), [("10", 50.0, True)], mood=None)
    _sesion(det_cli, date.today() - timedelta(days=1), [("10", 50.0, True)], mood=4)

    por_fecha = {f["fecha"]: f for f in _historial(client, h_coach, det_cli)["sesiones"]}
    assert por_fecha[date.today().isoformat()]["mood"] is None
    assert por_fecha[(date.today() - timedelta(days=1)).isoformat()]["mood"] == 4


# ── Y que no lo vea cualquiera ─────────────────────────────────────────────

def test_un_cliente_no_ve_el_historial_por_esta_puerta(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _h_coach, det_cli = _monta(client, admin_headers, suf)
    _uid, _det, h_otro = _crear_usuario(
        client, admin_headers, f"cli.fisgon.{suf}@nutrientrena-qa.com", role_id=6)
    r = client.get(f"/api/session-logs/client/{det_cli}/historial", headers=h_otro)
    assert r.status_code == 403, r.status_code


# ── El día de la rutina ────────────────────────────────────────────────────

def test_LA_COLUMNA_SESION_DICE_EL_DIA_NO_LA_RUTINA(client, seed, admin_headers):
    """El prototipo enseña "Día 4". Con solo la rutina, las cincuenta filas
    dirían el mismo texto y la columna no informaría de nada."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    db = SessionLocal()
    try:
        s = WorkoutSession(client_user_detail_id=det_cli, session_date=date.today(),
                           day_name="Día 4", duration_min=38)
        db.add(s)
        db.commit()
    finally:
        db.close()

    fila = _historial(client, h_coach, det_cli)["sesiones"][0]
    assert fila["sesion"] == "Día 4", fila["sesion"]


def test_una_sesion_vieja_sin_dia_no_se_queda_sin_nombre(client, seed, admin_headers):
    """Las que ya estaban registradas no lo tienen. Mejor el nombre de la
    rutina que un hueco."""
    suf = uuid.uuid4().hex[:8]
    h_coach, det_cli = _monta(client, admin_headers, suf)
    _sesion(det_cli, date.today(), [("10", 50.0, True)])
    fila = _historial(client, h_coach, det_cli)["sesiones"][0]
    assert fila["sesion"] == "Entreno", fila["sesion"]
