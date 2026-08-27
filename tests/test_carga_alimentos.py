"""La limpieza y carga del catálogo nuevo de alimentos.

Es una operación de una sola vez sobre la base de producción, así que lo que
hay que comprobar no es que "funcione": es que se lleve por delante SOLO lo
acordado.

  · Se borran alimentos, dietas, recetas, rutinas y menús semanales.
  · Se CONSERVA el historial de entrenos de los clientes. Es el registro de lo
    que la persona hizo de verdad y no se recupera de ningún sitio; al borrar
    las rutinas se le suelta la referencia, no se borra la sesión.
  · Los usuarios de prueba se dan de baja, no se borran en duro: `users.id`
    cuelga de decenas de tablas y un borrado físico deja huecos.
  · Y el modo simulacro no puede escribir NADA. Es lo único que separa una
    migración de un accidente.
"""
import sys
import uuid
from datetime import date

import pytest

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment, AlimentDescription
from app.models.nutrition.diet import Diet, DietFood, DietFoodAliment
from app.models.nutrition.recipe import Recipe, RecipeDetail
from app.models.routine import Routine, RoutineDay
from app.models.session_log import WorkoutSession
from app.models.user import UserDetail

from scripts.limpiar_y_cargar_alimentos import cargar, leer_csv, limpiar, usuarios_de_prueba

CSV_CABECERA = (
    "id,Nombre,Grupo de alimento,Marca,Cantidad,Unidad,Calorias,Proteinas,"
    "Carbohidratos,Grasas,Fibra,vitA,calcium,iron,tiene_micros,es_duplicado,"
    "momento_sugerido,comments\n"
)


def _csv(tmp_path, filas):
    ruta = tmp_path / "alimentos.csv"
    ruta.write_text(CSV_CABECERA + "".join(filas), encoding="utf-8")
    return str(ruta)


@pytest.fixture
def sesion():
    """Sesión propia. `db` ya existe en conftest y es de otro ámbito."""
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def _monta_datos(sesion, suf):
    """Una dieta, una receta, una rutina y una sesión de entreno ya hecha."""
    al = Aliment(id=str(uuid.uuid4()), name=f"Alimento viejo {suf}", calories=100.0)
    sesion.add(al)
    sesion.flush()
    sesion.add(AlimentDescription(aliment_id=al.id, iron=2.0))

    dieta = Diet(id=str(uuid.uuid4()), title=f"Dieta vieja {suf}")
    sesion.add(dieta)
    sesion.flush()
    comida = DietFood(diet_id=dieta.id, name="Desayuno")
    sesion.add(comida)
    sesion.flush()
    sesion.add(DietFoodAliment(diet_id=dieta.id, diet_food_id=comida.id,
                               aliment_id=al.id, quantity=100.0, order=0))

    receta = Recipe(name=f"Receta vieja {suf}")
    sesion.add(receta)
    sesion.flush()
    sesion.add(RecipeDetail(recipe_id=receta.id, aliment_id=al.id, quantity=50.0))

    rutina = Routine(name=f"Rutina vieja {suf}")
    sesion.add(rutina)
    sesion.flush()
    sesion.add(RoutineDay(routine_id=rutina.id, day_name="Día 1"))

    detalle = sesion.query(UserDetail).first()
    entreno = WorkoutSession(client_user_detail_id=detalle.id, routine_id=rutina.id,
                             session_date=date.today())
    sesion.add(entreno)
    sesion.commit()
    return al.id, dieta.id, receta.id, rutina.id, entreno.id


# ── Lo que se borra y lo que no ────────────────────────────────────────────

def test_SE_BORRA_LO_ACORDADO_Y_SE_QUEDA_EL_HISTORIAL(client, seed, admin_headers, sesion):
    """El historial de entrenos es el registro de lo que el cliente hizo de
    verdad. Se le suelta la rutina, no se borra la sesión."""
    suf = uuid.uuid4().hex[:8]
    _al, _d, _r, rutina_id, sesion_id = _monta_datos(sesion, suf)

    limpiar(sesion, ["%@nutrientrena-qa.com"])
    sesion.commit()

    assert sesion.query(Aliment).count() == 0
    assert sesion.query(Diet).count() == 0
    assert sesion.query(Recipe).count() == 0
    assert sesion.query(Routine).count() == 0
    assert sesion.query(DietFood).count() == 0
    assert sesion.query(RecipeDetail).count() == 0

    # Y el entreno sigue ahí, sin rutina.
    entreno = sesion.query(WorkoutSession).filter(WorkoutSession.id == sesion_id).first()
    assert entreno is not None, "se ha perdido el historial de entrenos"
    assert entreno.routine_id is None, entreno.routine_id
    assert entreno.session_date == date.today()
    del rutina_id


def test_los_usuarios_de_prueba_se_dan_de_baja_no_se_borran(client, seed, admin_headers, sesion):
    """Borrarlos en duro deja huecos en las decenas de tablas que cuelgan de
    `users.id`. La baja los saca de en medio sin romper nada."""
    from tests.test_org_scope import _crear_usuario
    suf = uuid.uuid4().hex[:8]
    _uid, det_id, _h = _crear_usuario(
        client, admin_headers, f"cli.carga.{suf}@nutrientrena-qa.com", role_id=6)

    assert any(f[0] == det_id for f in usuarios_de_prueba(sesion, ["%@nutrientrena-qa.com"]))
    limpiar(sesion, ["%@nutrientrena-qa.com"])
    sesion.commit()

    ud = sesion.query(UserDetail).filter(UserDetail.id == det_id).first()
    assert ud is not None, "el usuario se ha borrado en duro"
    assert ud.deleted_at is not None, "el usuario no se ha dado de baja"


def test_NO_TOCA_A_LOS_USUARIOS_QUE_NO_SON_DE_PRUEBA(client, seed, admin_headers, sesion):
    """Lo que de verdad protege esto: un patrón demasiado ancho daría de baja a
    clientes reales, y eso no se ve hasta que uno no puede entrar."""
    from tests.test_org_scope import _crear_usuario
    suf = uuid.uuid4().hex[:8]
    _uid, det_real, _h = _crear_usuario(
        client, admin_headers, f"persona.real.{suf}@gmail.com", role_id=6)

    limpiar(sesion, ["%@nutrientrena-qa.com"])
    sesion.commit()

    ud = sesion.query(UserDetail).filter(UserDetail.id == det_real).first()
    assert ud.deleted_at is None, "se ha dado de baja a alguien que no era de prueba"


def test_EL_PATRON_POR_DEFECTO_NO_ALCANZA_A_NADIE_REAL(client, seed, admin_headers, sesion):
    """El riesgo de verdad no es el patrón que se escribe a mano: es el que
    trae puesto el script. Quien lo lance sin `--patron-prueba` se lleva ese, y
    si alguien lo aflojara ("%@%") daría de baja a la cartera entera sin que
    ninguna otra comprobación se enterara — lo comprobé aflojándolo.
    """
    from scripts.limpiar_y_cargar_alimentos import PATRONES_PRUEBA
    from tests.test_org_scope import _crear_usuario
    suf = uuid.uuid4().hex[:8]
    _uid, det_real, _h = _crear_usuario(
        client, admin_headers, f"persona.real.{suf}@gmail.com", role_id=6)

    alcanzados = [f[0] for f in usuarios_de_prueba(sesion, PATRONES_PRUEBA)]
    assert det_real not in alcanzados, (
        f"el patrón por defecto {PATRONES_PRUEBA} alcanza a un correo normal")


# ── La carga ───────────────────────────────────────────────────────────────

def test_carga_los_alimentos_con_su_categoria_y_sus_micros(client, seed, admin_headers, sesion, tmp_path):
    suf = uuid.uuid4().hex[:8]
    ruta = _csv(tmp_path, [
        f"1,pollo a la plancha {suf},Aves,,100,gr,165.0,31.0,0.0,3.6,0.0,0.0,15.0,1.0,True,False,,\n",
        f"2,Avena {suf},Cereales y granos,Hacendado,100,gr,389.0,16.9,66.3,6.9,10.6,0.0,54.0,4.7,True,False,Desayuno,\n",
    ])
    alimentos, _avisos = leer_csv(ruta)
    limpiar(sesion, [])
    cargar(sesion, alimentos, None, None)
    sesion.commit()

    pollo = sesion.query(Aliment).filter(Aliment.name.like(f"%{suf}%"),
                                        Aliment.name.like("Pollo%")).first()
    # El nombre venía en minúscula: en la biblioteca queda como un renglón
    # desordenado entre 800.
    assert pollo is not None and pollo.name.startswith("Pollo"), pollo
    assert pollo.calories == 165.0 and pollo.proteins == 31.0
    # `gr` es lo que trae el CSV; la plataforma usa `g`.
    assert pollo.quantity_unit == "g", pollo.quantity_unit
    assert pollo.group_food is not None and pollo.group_food.name == "Aves"

    avena = sesion.query(Aliment).filter(Aliment.name.like(f"Avena {suf}%")).first()
    assert avena.brand == "Hacendado", avena.brand
    assert avena.meal_moments == "Desayuno", avena.meal_moments
    desc = sesion.query(AlimentDescription).filter(
        AlimentDescription.aliment_id == avena.id).first()
    assert desc is not None and desc.fiber == 10.6 and desc.iron == 4.7


def test_DE_DOS_REPETIDOS_SE_QUEDA_EL_QUE_TRAE_MICRONUTRIENTES(client, seed, admin_headers, sesion, tmp_path):
    """El CSV trae 19 nombres por duplicado. La copia sin micronutrientes es la
    que metió a mano algún cliente; quedarse con esa perdería los datos buenos.
    """
    suf = uuid.uuid4().hex[:8]
    ruta = _csv(tmp_path, [
        f"1,Almendras {suf},Frutos secos y semillas,,100,gr,600.0,20.0,20.0,50.0,,,,,False,True,,\n",
        f"2,Almendras {suf},Frutos secos y semillas,,100,gr,616.0,21.2,21.6,49.9,12.5,0.0,269.0,3.7,True,True,,\n",
    ])
    alimentos, avisos = leer_csv(ruta)
    assert len(alimentos) == 1, alimentos
    assert alimentos[0]["calorias"] == 616.0, alimentos[0]
    assert any("repetido" in a for a in avisos), avisos

    limpiar(sesion, [])
    cargar(sesion, alimentos, None, None)
    sesion.commit()
    guardado = sesion.query(Aliment).filter(Aliment.name.like(f"Almendras {suf}%")).all()
    assert len(guardado) == 1 and guardado[0].calories == 616.0


def test_el_repetido_se_descarta_en_cualquier_orden(client, seed, admin_headers, sesion, tmp_path):
    """Si el bueno viene primero, tampoco lo pisa el malo."""
    suf = uuid.uuid4().hex[:8]
    ruta = _csv(tmp_path, [
        f"1,Coco {suf},Frutas,,100,gr,354.0,3.3,15.2,33.5,9.0,0.0,14.0,2.4,True,True,,\n",
        f"2,Coco {suf},Frutas,,100,gr,300.0,3.0,15.0,30.0,,,,,False,True,,\n",
    ])
    alimentos, _a = leer_csv(ruta)
    assert len(alimentos) == 1 and alimentos[0]["calorias"] == 354.0, alimentos


def test_las_categorias_no_se_duplican_al_cargar(client, seed, admin_headers, sesion, tmp_path):
    """Se crean las que faltan; las que ya están se reutilizan. Sin esto, cada
    carga dejaría "Aves" repetida y la biblioteca saldría con dos secciones que
    se llaman igual."""
    from app.models.nutrition.group_food import GroupFood
    suf = uuid.uuid4().hex[:8]
    sesion.add(GroupFood(name="Aves"))
    sesion.commit()
    antes = sesion.query(GroupFood).filter(GroupFood.name == "Aves").count()

    ruta = _csv(tmp_path, [
        f"1,Pavo {suf},Aves,,100,gr,135.0,29.0,0.0,1.0,,,,,False,False,,\n"])
    alimentos, _a = leer_csv(ruta)
    cargar(sesion, alimentos, None, None)
    sesion.commit()
    assert sesion.query(GroupFood).filter(GroupFood.name == "Aves").count() == antes


def test_una_fila_sin_nombre_no_para_la_carga(client, seed, admin_headers, sesion, tmp_path):
    suf = uuid.uuid4().hex[:8]
    ruta = _csv(tmp_path, [
        ",,Frutas,,100,gr,50.0,0.0,12.0,0.0,,,,,False,False,,\n",
        f"2,Manzana {suf},Frutas,,100,gr,52.0,0.3,14.0,0.2,,,,,False,False,,\n",
    ])
    alimentos, avisos = leer_csv(ruta)
    assert len(alimentos) == 1 and alimentos[0]["nombre"].startswith("Manzana")
    assert any("sin nombre" in a for a in avisos), avisos


# ── Cómo se comporta cuando algo va mal ────────────────────────────────────
#
# Estas no comprueban la carga, sino lo que el script DICE. Un script que se
# ejecuta a mano contra producción se usa mirando su salida: si miente sobre el
# estado de los datos, da igual que por dentro esté bien.

def test_COMPROBAR_NO_EXIGE_PASAR_EL_CSV(monkeypatch, tmp_path):
    """`--csv` era obligatorio hasta para `--verificar`, que no carga nada.
    Salía un error de uso, no un informe, y desde el otro lado eso parece que
    el script está roto.
    """
    from scripts import limpiar_y_cargar_alimentos as mod

    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "x.db"))
    monkeypatch.setattr(sys, "argv", ["x", "--verificar"])
    monkeypatch.setattr(mod, "verificar", lambda db, alimentos: 0)
    assert mod.main() == 0          # antes: SystemExit(2) de argparse


def test_SIN_CSV_NO_DICE_QUE_SE_ESPERABAN_CERO(monkeypatch, capsys, client, seed, sesion):
    """Sin fichero con el que comparar no hay número esperado. Escribir
    "(se esperaban 0)" se lee como que la base tenía que estar vacía."""
    from scripts.limpiar_y_cargar_alimentos import verificar

    verificar(sesion, [])
    linea = next(ln for ln in capsys.readouterr().out.splitlines()
                 if "alimentos" in ln)
    assert "se esperaban" not in linea, linea
    # La de "sin categoría" SÍ lleva su cero, y ahí es cierto: no puede quedar
    # ninguno suelto, venga el CSV o no.


def test_NO_PODER_CONECTAR_NO_SE_CUENTA_COMO_CERO_ALIMENTOS(monkeypatch, capsys, tmp_path):
    """El fallo que hizo creer que se había borrado el catálogo entero.

    `_cuenta()` se tragaba cualquier excepción y devolvía None, que se imprime
    como 0. Con la contraseña mal puesta, la salida era «0 alimentos (se
    esperaban 784)» — indistinguible de una base vaciada.
    """
    from scripts import limpiar_y_cargar_alimentos as mod

    class _SesionRota:
        def execute(self, *a, **k):
            raise RuntimeError('(1045, "Access denied for user \'root\'@\'x\'")')

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://root:mala@h:3306/railway")
    monkeypatch.setattr(sys, "argv", ["x", "--verificar"])
    monkeypatch.setattr(mod, "SessionLocal", lambda: _SesionRota())

    assert mod.main() == 1
    cap = capsys.readouterr()
    todo = cap.out + cap.err
    assert "No se ha podido conectar" in todo, todo
    assert "No se ha leído ni tocado nada" in todo, todo
    # Y sobre todo: ni una cifra de alimentos, que es lo que asustaba.
    assert "alimentos" not in todo, todo


def test_una_tabla_que_no_existe_si_se_perdona(monkeypatch):
    """Que es para lo que estaba puesto el `except`: bases sin migrar del todo.
    Perdonar eso está bien; perdonar TODO era el fallo."""
    from scripts.limpiar_y_cargar_alimentos import _cuenta

    class _Falta:
        def execute(self, *a, **k):
            raise RuntimeError("(1146, \"Table 'railway.recipes' doesn't exist\")")

        def rollback(self):
            pass

    assert _cuenta(_Falta(), "recipes") is None

    class _Otro:
        def execute(self, *a, **k):
            raise RuntimeError("Lost connection to MySQL server during query")

        def rollback(self):
            pass

    with pytest.raises(RuntimeError):
        _cuenta(_Otro(), "aliments")
