"""Ver una pieza de contenido de una cuenta antes de subirla a la plataforma.

Promover pone ese contenido delante de TODAS las cuentas, y hasta ahora la
decisión se tomaba viendo solo el nombre y de quién era. Esta ficha enseña lo
que hay dentro.

Lo que más importa aquí no son los campos, es el aviso: promover cambia el
ámbito de la pieza y de nada más, así que una rutina que use ejercicios
privados de esa cuenta se vería con huecos en las demás. Eso no se arregla solo
—subir cosas que nadie ha pedido sería peor— pero sí se dice.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.diet import Diet, DietFood, DietFoodAliment
from app.models.routine import Routine, RoutineBlock, RoutineDay, RoutineDayDetail
from app.models.training import Training

from tests.test_org_scope import _crear_coach, _crear_organizacion


def _ficha(client, headers, tipo, id_):
    return client.get(f"/api/admin/content/{tipo}/{id_}/detalle", headers=headers)


def _cuenta(client, admin_headers, suf):
    _uid, det, _h = _crear_coach(client, admin_headers, f"coach.ficha.{suf}@nutrientrena-qa.com")
    return _crear_organizacion(det, f"Centro Ficha {suf}")


def _rutina_con_ejercicios(org_id, suf, privados: int, globales: int):
    """Una rutina de esa cuenta con un día y un bloque de ejercicios."""
    db = SessionLocal()
    try:
        rut = Routine(name=f"Rutina ficha {suf}", organization_id=org_id,
                      objective="Hipertrofia", days=3, time=8, notes="Progresión semanal")
        db.add(rut)
        db.flush()
        dia = RoutineDay(routine_id=rut.id, day_name="Día 1 · Empuje")
        db.add(dia)
        db.flush()
        blq = RoutineBlock(routine_id=rut.id, routine_day_id=dia.id, block_type="normal")
        db.add(blq)
        db.flush()

        for i in range(privados):
            t = Training(name=f"Ejercicio privado {i} {suf}", state=1, organization_id=org_id)
            db.add(t)
            db.flush()
            db.add(RoutineDayDetail(routine_id=rut.id, routine_day_id=dia.id, block_id=blq.id,
                                    training_id=t.id, series=4, repetitions="10", break_time=90))
        for i in range(globales):
            t = Training(name=f"Ejercicio común {i} {suf}", state=1, organization_id=None)
            db.add(t)
            db.flush()
            db.add(RoutineDayDetail(routine_id=rut.id, routine_day_id=dia.id, block_id=blq.id,
                                    training_id=t.id, series=3, repetitions="12", break_time=60))
        db.commit()
        return rut.id
    finally:
        db.close()


def _dieta_con_alimentos(org_id, suf, privados: int):
    db = SessionLocal()
    try:
        dieta = Diet(title=f"Dieta ficha {suf}", organization_id=org_id, calories=2100,
                     notes="Cinco comidas")
        db.add(dieta)
        db.flush()
        comida = DietFood(diet_id=dieta.id, name="Desayuno", time="08:30")
        db.add(comida)
        db.flush()
        for i in range(privados):
            al = Aliment(name=f"Alimento privado {i} {suf}", calories=120, organization_id=org_id)
            db.add(al)
            db.flush()
            db.add(DietFoodAliment(diet_id=dieta.id, diet_food_id=comida.id,
                                   aliment_id=al.id, quantity=100))
        db.commit()
        return dieta.id
    finally:
        db.close()


# ── Lo que enseña ──────────────────────────────────────────────────────────

def test_la_ficha_de_una_rutina_trae_sus_dias_y_sus_ejercicios(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org = _cuenta(client, admin_headers, suf)
    rid = _rutina_con_ejercicios(org, suf, privados=0, globales=2)

    r = _ficha(client, admin_headers, "routines", rid)
    assert r.status_code == 200, r.text
    d = r.json()["data"]

    assert d["nombre"] == f"Rutina ficha {suf}"
    assert d["etiqueta"] == "Rutinas"
    assert d["cuenta"]["id"] == org
    assert d["en_plataforma"] is False
    assert d["promover"] == "routine"

    campos = {c["etiqueta"]: c["valor"] for c in d["campos"]}
    assert campos["Objetivo"] == "Hipertrofia"
    assert campos["Días por semana"] == "3"
    assert campos["Ejercicios en total"] == "2"

    assert len(d["bloques"]) == 1
    bloque = d["bloques"][0]
    assert bloque["titulo"] == "Día 1 · Empuje"
    assert len(bloque["filas"]) == 2
    # Nombre del ejercicio, series, reps y descanso: lo que hace falta para
    # juzgar si la rutina está bien hecha.
    assert any("Ejercicio común 0" in celda for celda in bloque["filas"][0])
    assert "3" in bloque["filas"][0] and "12" in bloque["filas"][0]


def test_la_ficha_de_una_dieta_trae_sus_comidas(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org = _cuenta(client, admin_headers, suf)
    did = _dieta_con_alimentos(org, suf, privados=1)

    d = _ficha(client, admin_headers, "diets", did).json()["data"]
    assert d["etiqueta"] == "Dietas"
    campos = {c["etiqueta"]: c["valor"] for c in d["campos"]}
    assert campos["Calorías"] == "2100"
    assert campos["Comidas"] == "1"
    assert d["bloques"][0]["titulo"] == "Desayuno"
    assert d["bloques"][0]["subtitulo"] == "08:30"


def test_la_ficha_de_un_ejercicio_dice_en_cuantas_rutinas_se_usa(client, seed, admin_headers):
    """Un ejercicio suelto no tiene "dentro", así que lo útil para decidir es
    si alguien lo está usando de verdad."""
    suf = uuid.uuid4().hex[:8]
    org = _cuenta(client, admin_headers, suf)
    _rutina_con_ejercicios(org, suf, privados=1, globales=0)

    db = SessionLocal()
    try:
        t = db.query(Training).filter(Training.name == f"Ejercicio privado 0 {suf}").first()
        tid = t.id
    finally:
        db.close()

    d = _ficha(client, admin_headers, "trainings", tid).json()["data"]
    campos = {c["etiqueta"]: c["valor"] for c in d["campos"]}
    assert campos["Se usa en"] == "1 rutina", campos


def test_la_ficha_de_un_alimento_trae_sus_macros(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org = _cuenta(client, admin_headers, suf)
    db = SessionLocal()
    try:
        al = Aliment(name=f"Pechuga ficha {suf}", organization_id=org, calories=165,
                     proteins=31, carbohydrates=0, fats=4, quantity=100)
        db.add(al)
        db.commit()
        aid = al.id
    finally:
        db.close()

    d = _ficha(client, admin_headers, "aliments", aid).json()["data"]
    campos = {c["etiqueta"]: c["valor"] for c in d["campos"]}
    assert campos["Calorías"] == "165" and campos["Proteínas"] == "31"
    assert campos["Ración"] == "100 g"


# ── El aviso, que es el motivo de la pantalla ──────────────────────────────

def test_avisa_si_la_rutina_usa_ejercicios_privados_de_la_cuenta(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org = _cuenta(client, admin_headers, suf)
    rid = _rutina_con_ejercicios(org, suf, privados=2, globales=1)

    dep = _ficha(client, admin_headers, "routines", rid).json()["data"]["dependencias_privadas"]
    assert dep is not None, "subir esta rutina la dejaría con huecos y no se decía"
    assert dep["cuantas"] == 2, dep
    assert all("privado" in n for n in dep["nombres"]), dep


def test_no_avisa_si_todo_lo_que_usa_ya_es_de_la_plataforma(client, seed, admin_headers):
    """La otra mitad: un aviso que sale siempre no informa de nada."""
    suf = uuid.uuid4().hex[:8]
    org = _cuenta(client, admin_headers, suf)
    rid = _rutina_con_ejercicios(org, suf, privados=0, globales=3)

    d = _ficha(client, admin_headers, "routines", rid).json()["data"]
    assert d["dependencias_privadas"] is None, d["dependencias_privadas"]


def test_avisa_tambien_en_las_dietas_con_alimentos_privados(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    org = _cuenta(client, admin_headers, suf)
    did = _dieta_con_alimentos(org, suf, privados=2)

    dep = _ficha(client, admin_headers, "diets", did).json()["data"]["dependencias_privadas"]
    assert dep is not None and dep["cuantas"] == 2, dep


# ── Errores y permisos ─────────────────────────────────────────────────────

def test_un_tipo_sin_ficha_lo_dice(client, seed, admin_headers):
    r = _ficha(client, admin_headers, "muscle_groups", 1)
    assert r.status_code == 400, r.text


def test_un_id_que_no_existe_da_404(client, seed, admin_headers):
    assert _ficha(client, admin_headers, "routines", 99999999).status_code == 404


def test_un_coach_no_puede_abrir_la_ficha(client, seed, admin_headers):
    """Es una pantalla del panel de plataforma: enseña contenido de cuentas
    ajenas, que es justo lo que un coach no tiene que ver."""
    suf = uuid.uuid4().hex[:8]
    org = _cuenta(client, admin_headers, suf)
    rid = _rutina_con_ejercicios(org, suf, privados=0, globales=1)
    _uid, _det, hc = _crear_coach(client, admin_headers, f"coach.fuera.{suf}@nutrientrena-qa.com")
    assert _ficha(client, hc, "routines", rid).status_code == 403


def test_sin_sesion_tampoco(client, seed):
    assert client.get("/api/admin/content/routines/1/detalle").status_code in (401, 403)
