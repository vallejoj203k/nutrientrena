"""Vaciar el contenido de nutrición/entrenamiento y cargar el catálogo nuevo.

Es una operación de una sola vez, acordada con el cliente:

  · Se BORRAN: alimentos, dietas, recetas, rutinas y los menús semanales (que
    sin dietas se quedan vacíos y no son más que un cascarón).
  · Se CONSERVA el historial de entrenos de los clientes: las sesiones que ya
    hicieron se quedan, sueltas de la rutina que las originó. Es el registro de
    lo que la persona hizo de verdad, y no se recupera de ningún sitio.
  · Los usuarios de prueba se dan de BAJA, no se borran en duro. `users.id`
    cuelga de decenas de tablas —dietas, check-ins, chat, contratos— y un
    borrado físico deja huecos que revientan pantallas semanas después. La baja
    los saca de los listados y les impide entrar, que es lo que se buscaba.

Por defecto NO escribe nada: cuenta lo que haría y lo enseña. Con 800 filas y
varias tablas por delante, ver los números antes es la diferencia entre una
migración y un accidente.

    python scripts/limpiar_y_cargar_alimentos.py --csv alimentos.csv
    python scripts/limpiar_y_cargar_alimentos.py --csv alimentos.csv --ejecutar

Antes de `--ejecutar`: copia de seguridad. Esto no se deshace.
"""
import argparse
import csv
import io
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text                                    # noqa: E402

from app.database import SessionLocal                          # noqa: E402


def _contra_que_base():
    """Host y nombre de la base, sin la contraseña.

    Un script que borra tiene que decir SIEMPRE dónde va a borrar. Y sin
    DATABASE_URL la aplicación se cae a una base local por defecto: alguien
    podría lanzar esto creyendo que apunta a producción, ver "Hecho." y no
    haber tocado nada de lo que creía.
    """
    from app.config import SQLALCHEMY_DATABASE_URL
    url = SQLALCHEMY_DATABASE_URL
    if "@" in url:
        esquema, resto = url.split("://", 1)
        return f"{esquema}://…@{resto.split('@', 1)[1]}"
    return url

# Correos que usan las pruebas automáticas. Solo este patrón por defecto: los
# demás dominios que aparecen en el repo (@test.com, @ejemplo.com) pueden ser
# de tandas viejas o de alguien real, y no se tocan sin confirmarlo.
PATRONES_PRUEBA = ["%@nutrientrena-qa.com"]

# La unidad de la plataforma es `g`; el CSV trae `gr`. Y viene una fila con `u`
# suelta entre 22 con `ud`. `tz` (taza) es una unidad de servicio, como `ud`.
UNIDADES = {"gr": "g", "g": "g", "ud": "ud", "u": "ud", "ml": "ml", "tz": "ud"}

COL = {
    "nombre": "Nombre", "grupo": "Grupo de alimento", "marca": "Marca",
    "cantidad": "Cantidad", "unidad": "Unidad", "calorias": "Calorias",
    "proteinas": "Proteinas", "carbohidratos": "Carbohidratos", "grasas": "Grasas",
    "momento": "momento_sugerido", "micros": "tiene_micros", "comments": "comments",
}

# Micronutrientes: cabecera del CSV -> columna de aliment_descriptions.
MICROS = {
    "Fibra": "fiber", "vitA": "vita", "vitB1": "vitb1", "vitB2": "vitb2",
    "vitB3": "vitb3", "vitB5": "vitb5", "vitB6": "vitb6", "vitB9": "vitb9",
    "vitB12": "vitb12", "vitC": "vitc", "vitD": "vitd", "vitE": "vite",
    "vitK": "vitk", "choline": "calina", "calcium": "calcium", "copper": "copper",
    "iron": "iron", "magnesium": "magnesium", "manganese": "manganese",
    "phosphorus": "phosphorus", "potassium": "potassium", "selenium": "selenium",
    "sodium": "sodium", "zinc": "zinc", "water": "water",
    "cholesterol": "cholesterol", "saturatedFat": "saturated_fats",
    "monoUnsaturatedFat": "mono_saturated_fats",
    "polyUnsaturatedFat": "poli_saturated_fats", "glycemicIndex": "glycemic_index",
}


def _num(v):
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _clave(nombre):
    """Para comparar nombres: sin tildes, sin mayúsculas, sin espacios de más."""
    s = unicodedata.normalize("NFKD", (nombre or "").strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.split())


def _titulo(nombre):
    """'aceite oleico gourmet' -> 'Aceite oleico gourmet'. 120 filas vienen en
    minúscula y en la biblioteca quedan como un renglón desordenado."""
    s = " ".join((nombre or "").split())
    return s[:1].upper() + s[1:] if s else s


# ── Leer y limpiar el CSV ──────────────────────────────────────────────────

def leer_csv(ruta):
    """Devuelve (alimentos, avisos). No toca la base de datos."""
    with open(ruta, "rb") as fh:
        crudo = fh.read()
    try:
        texto = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = crudo.decode("latin-1")

    brutos, avisos = [], []
    for f in csv.DictReader(io.StringIO(texto)):
        nombre = _titulo(f.get(COL["nombre"], ""))
        if not nombre:
            avisos.append("una fila sin nombre, descartada")
            continue
        unidad = (f.get(COL["unidad"], "") or "g").strip().lower()
        if unidad and unidad not in UNIDADES:
            avisos.append(f"'{nombre}': unidad desconocida '{unidad}', se usa g")
        brutos.append({
            "nombre": nombre,
            "grupo": (f.get(COL["grupo"], "") or "").strip() or None,
            "marca": (f.get(COL["marca"], "") or "").strip() or None,
            "cantidad": _num(f.get(COL["cantidad"])),
            "unidad": UNIDADES.get(unidad, "g"),
            "calorias": _num(f.get(COL["calorias"])),
            "proteinas": _num(f.get(COL["proteinas"])),
            "carbohidratos": _num(f.get(COL["carbohidratos"])),
            "grasas": _num(f.get(COL["grasas"])),
            "momento": (f.get(COL["momento"], "") or "").strip() or None,
            "comments": (f.get(COL["comments"], "") or "").strip() or None,
            "tiene_micros": f.get(COL["micros"], "") == "True",
            "micros": {d: _num(f.get(c)) for c, d in MICROS.items()
                       if _num(f.get(c)) is not None},
        })

    # De dos filas con el mismo nombre se queda la que TIENE micronutrientes:
    # la otra trae solo macros y es la que metió a mano algún cliente. Si las
    # dos empatan, la primera. Son los 19 nombres repetidos del CSV.
    mejor, orden = {}, []
    for x in brutos:
        k = _clave(x["nombre"])
        if k not in mejor:
            mejor[k] = x
            orden.append(k)
        else:
            previo = mejor[k]
            if x["tiene_micros"] and not previo["tiene_micros"]:
                mejor[k] = x
                avisos.append(f"repetido '{x['nombre']}': se queda el que trae micronutrientes")
            else:
                avisos.append(f"repetido '{x['nombre']}': se descarta la copia")

    return [mejor[k] for k in orden], avisos


# ── Lo que se va a borrar ──────────────────────────────────────────────────
#
# El orden va de dentro afuera. Al revés falla a mitad por las claves ajenas y
# deja la base a medio vaciar, que es peor que no haber empezado.
BORRADOS = [
    ("recipe_details",       "ingredientes de las recetas"),
    ("recipes",              "recetas"),
    ("diet_food_aliments",   "alimentos dentro de las dietas"),
    ("diet_foods",           "comidas de las dietas"),
    ("diet_details",         "objetivos de las dietas"),
    ("diet_pathologies",     "patologías de las dietas"),
    ("client_menus",         "menús semanales asignados a clientes"),
    ("weekly_menu_days",     "días de los menús semanales"),
    ("weekly_menus",         "menús semanales"),
    ("diets",                "dietas"),
    ("routine_day_details",  "ejercicios de las rutinas"),
    ("routine_blocks",       "bloques de las rutinas"),
    ("routine_days",         "días de las rutinas"),
    ("routines",             "rutinas"),
    ("aliment_descriptions", "micronutrientes de los alimentos"),
    ("aliments",             "alimentos"),
]

# Lo que NO se borra pero suelta la referencia, para no llevárselo por delante.
DESVINCULAR = [
    ("workout_sessions", "routine_id",
     "sesiones de entreno ya registradas (se conservan, sin rutina)"),
    ("plan_deliveries", "diet_id", "envíos de dieta por correo"),
    ("plan_deliveries", "routine_id", "envíos de rutina por correo"),
    ("aliments", "parent_id", "alimentos que copiaban a otro"),
]


def inspeccionar(db, alimentos):
    """Qué son los alimentos que ya hay, para decidir si se pueden tirar.

    Los números del informe dicen CUÁNTOS hay, no QUÉ son. Con 7460 originales
    frente a 784 en el CSV, la pregunta no es cuántos sino si el CSV es el
    catálogo entero o solo un trozo — y eso solo se ve mirando los nombres.
    """
    print("\n╭─ QUÉ HAY EN LA BASE ─────────────────────────────────────────")

    filas = db.execute(text(
        "SELECT a.name, a.brand, g.name FROM aliments a "
        "LEFT JOIN group_foods g ON g.id = a.group_food_id "
        "WHERE a.parent_id IS NULL ORDER BY a.name LIMIT 25")).fetchall()
    print("│  Una muestra de los originales:")
    for n, marca, grupo in filas:
        print(f"│    {(n or '')[:44]:<44} {(grupo or 'sin categoría')[:22]}")

    print("│")
    print("│  Por categoría:")
    for grupo, n in db.execute(text(
            "SELECT COALESCE(g.name,'(sin categoría)'), COUNT(*) FROM aliments a "
            "LEFT JOIN group_foods g ON g.id = a.group_food_id "
            "WHERE a.parent_id IS NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 12")).fetchall():
        print(f"│    {n:>6}  {grupo}")

    # La pregunta que decide: ¿el CSV es el catálogo entero o un trozo suyo?
    # Si casi todos sus nombres YA están, es una selección curada de lo que hay
    # y lo suyo es mezclar, no vaciar.
    en_base = {(r[0] or "").strip().lower()
               for r in db.execute(text(
                   "SELECT name FROM aliments WHERE parent_id IS NULL")).fetchall()}
    del_csv = {a["nombre"].strip().lower() for a in alimentos}
    ya_estan = len(del_csv & en_base)
    print("│")
    print("├─ ¿EL CSV ES EL CATÁLOGO ENTERO O UN TROZO? ──────────────────")
    print(f"│  {len(del_csv):>7}  nombres distintos trae el CSV")
    print(f"│  {ya_estan:>7}  de ellos YA están en la base")
    print(f"│  {len(del_csv) - ya_estan:>7}  serían nuevos")
    print(f"│  {len(en_base - del_csv):>7}  hay en la base que el CSV NO trae")
    print("│")
    if ya_estan > len(del_csv) * 0.6:
        print("│  El CSV es en su mayoría gente que ya está: parece una")
        print("│  selección revisada de lo que hay, no un catálogo nuevo.")
        print("│  Lo suyo entonces es MEZCLAR (actualizar los que trae y dejar")
        print("│  el resto), no vaciar. Vaciar tiraría los que no vienen.")
    else:
        print("│  El CSV trae sobre todo alimentos que no están: es catálogo")
        print("│  nuevo, no una revisión del que hay.")
    print("╰──────────────────────────────────────────────────────────────\n")


def verificar(db, alimentos):
    """Comprobar cómo quedó la base después de cargar.

    «Hecho.» no es una comprobación: dice que el script terminó, no que el
    catálogo esté bien. Lo que importa es que estén los que tenían que estar,
    con su categoría, y que las kcal salgan.
    """
    fallos = []
    print(f"\nBase de datos: {_contra_que_base()}")
    print("\n╭─ CÓMO QUEDÓ ────────────────────────────────────────────────")

    total = _cuenta(db, "aliments") or 0
    sin_cat = _cuenta(db, "aliments", "WHERE group_food_id IS NULL") or 0
    con_micros = _cuenta(db, "aliment_descriptions") or 0
    print(f"│  {total:>7}  alimentos           (se esperaban {len(alimentos)})")
    print(f"│  {sin_cat:>7}  sin categoría       (se esperaban 0)")
    print(f"│  {con_micros:>7}  con micronutrientes")
    if total != len(alimentos):
        fallos.append(f"hay {total} alimentos y se cargaron {len(alimentos)}")
    if sin_cat:
        fallos.append(f"{sin_cat} alimentos se han quedado sin categoría")

    print("│")
    print("│  Categorías:")
    for nombre, n in db.execute(text(
            "SELECT COALESCE(g.name,'(ninguna)'), COUNT(*) FROM aliments a "
            "LEFT JOIN group_foods g ON g.id = a.group_food_id "
            "GROUP BY 1 ORDER BY 2 DESC")).fetchall():
        print(f"│    {n:>5}  {nombre}")

    print("│")
    print("│  Unidades:")
    for u, n in db.execute(text(
            "SELECT COALESCE(quantity_unit,'(ninguna)'), COUNT(*) FROM aliments "
            "GROUP BY 1 ORDER BY 2 DESC")).fetchall():
        print(f"│    {n:>5}  {u}")

    # Lo viejo tiene que haberse ido: si queda algo, el borrado falló a medias.
    print("│")
    print("│  De lo viejo:")
    for tabla, rotulo in (("diets", "dietas"), ("recipes", "recetas"),
                          ("routines", "rutinas"), ("weekly_menus", "menús semanales")):
        n = _cuenta(db, tabla)
        print(f"│    {n:>5}  {rotulo}")
        if n:
            fallos.append(f"quedan {n} {rotulo}")

    # Y que las kcal salgan bien, que es de lo que va todo esto.
    fila = db.execute(text(
        "SELECT name, calories, quantity, quantity_unit FROM aliments "
        "WHERE quantity_unit = 'ud' AND quantity = 1 AND calories > 0 LIMIT 1")).fetchone()
    if fila:
        from app.core.macros import escalar

        class _A:
            pass
        a = _A()
        a.quantity = fila[2]
        dos = escalar(fila[1], a, 2)
        print("│")
        print(f"│  Prueba de kcal: {fila[0]} = {fila[1]} kcal por {fila[2]} {fila[3]}")
        print(f"│    dos unidades -> {dos} kcal  (bien si es {fila[1] * 2})")
        if abs(dos - fila[1] * 2) > 0.01:
            fallos.append("las kcal de un alimento por unidad salen mal")

    print("╰──────────────────────────────────────────────────────────────")
    if fallos:
        print("\nHAY PROBLEMAS:")
        for f in fallos:
            print(f"  · {f}")
        return 1
    print("\nTodo cuadra.\n")
    return 0


def _cuenta(db, tabla, donde=""):
    """Cuántas filas hay, o None si la tabla no existe.

    Solo se traga el «no existe esa tabla», que pasa en bases viejas. Cualquier
    otro problema —sobre todo NO PODER CONECTAR— se deja subir: si no, un fallo
    de conexión se convertía en «0 alimentos», y eso lo lee alguien y cree que
    se le ha borrado el catálogo entero.
    """
    try:
        return db.execute(text(f"SELECT COUNT(*) FROM {tabla} {donde}")).scalar() or 0
    except Exception as e:
        texto = str(e).lower()
        if "doesn't exist" in texto or "no such table" in texto or "unknown table" in texto:
            db.rollback()
            return None
        raise


def _existe(db, tabla):
    return _cuenta(db, tabla) is not None


def usuarios_de_prueba(db, patrones):
    filas = []
    for p in patrones:
        try:
            filas += db.execute(text(
                "SELECT ud.id, u.email FROM user_details ud "
                "JOIN users u ON u.id = ud.user_id "
                "WHERE u.email LIKE :p AND ud.deleted_at IS NULL"
            ), {"p": p}).fetchall()
        except Exception:
            pass
    return filas


# ── Informe ────────────────────────────────────────────────────────────────

def informe(db, alimentos, avisos, patrones):
    print(f"\nBase de datos: {_contra_que_base()}")
    print("\n╭─ SE VA A BORRAR ─────────────────────────────────────────────")
    total = 0
    for tabla, rotulo in BORRADOS:
        n = _cuenta(db, tabla)
        if n is None:
            print(f"│  (sin tabla {tabla})")
            continue
        total += n
        print(f"│  {n:>7}  {rotulo}")
    print(f"│  {total:>7}  filas en total")

    print("├─ SE CONSERVA, soltando la referencia ────────────────────────")
    for tabla, col, rotulo in DESVINCULAR:
        if not _existe(db, tabla):
            continue
        n = _cuenta(db, tabla, f"WHERE {col} IS NOT NULL")
        print(f"│  {n:>7}  {rotulo}")

    pruebas = usuarios_de_prueba(db, patrones)
    print("├─ USUARIOS DE PRUEBA (baja, no borrado) ──────────────────────")
    print(f"│  {len(pruebas):>7}  cuentas")
    for _id, email in pruebas[:10]:
        print(f"│           {email}")
    if len(pruebas) > 10:
        print(f"│           … y {len(pruebas) - 10} más")

    # ── De dónde salen los alimentos que hay ───────────────────────────────
    # Si en la base hay MUCHOS más de los que trae el CSV, vaciar y cargar
    # pierde la diferencia. Conviene saber si esos de más son copias —al
    # asignar una dieta se clonan alimentos, y esas copias llevan `parent_id`—
    # o catálogo de verdad que el CSV no incluye.
    total_al = _cuenta(db, "aliments") or 0
    if total_al:
        copias = _cuenta(db, "aliments", "WHERE parent_id IS NOT NULL") or 0
        de_org = _cuenta(db, "aliments", "WHERE organization_id IS NOT NULL") or 0
        # Copias que ya no usa ninguna dieta. Al meter un alimento en una dieta
        # se hace una copia suya, pero cuando esa copia deja de usarse nadie la
        # borra: se queda en la tabla para siempre. No sale en la biblioteca ni
        # se puede usar — es basura, y suele ser la mayoría de lo que sobra.
        huerfanas = _cuenta(
            db, "aliments",
            "WHERE parent_id IS NOT NULL AND id NOT IN "
            "(SELECT aliment_id FROM diet_food_aliments)") or 0
        util = total_al - huerfanas

        print("├─ DE DÓNDE SALEN LOS ALIMENTOS DE AHORA ──────────────────────")
        print(f"│  {total_al:>7}  en la base")
        print(f"│  {huerfanas:>7}  copias sueltas que ya no usa ninguna dieta (basura)")
        print(f"│  {util:>7}  de verdad, de los cuales:")
        print(f"│  {copias - huerfanas:>7}    · copias en uso por alguna dieta")
        print(f"│  {total_al - copias:>7}    · originales del catálogo")
        print(f"│  {de_org:>7}  de alguna cuenta; {total_al - de_org} del catálogo común")

        if util > len(alimentos) * 1.2:
            print("│")
            print(f"│  OJO: quitando la basura quedan {util} y el CSV trae"
                  f" {len(alimentos)}.")
            print("│  Vaciar y cargar PIERDE esa diferencia: parece que el CSV")
            print("│  no trae el catálogo entero. Compruébalo antes de seguir.")
        elif huerfanas:
            print("│")
            print(f"│  Los {huerfanas} de más son basura acumulada, no catálogo.")
            print("│  Vaciar y cargar se los lleva, que es lo que se quiere.")

    print("├─ SE VA A CARGAR ─────────────────────────────────────────────")
    grupos = sorted({a["grupo"] for a in alimentos if a["grupo"]})
    con_micros = sum(1 for a in alimentos if a["micros"])
    con_marca = sum(1 for a in alimentos if a["marca"])
    con_momento = sum(1 for a in alimentos if a["momento"])
    print(f"│  {len(alimentos):>7}  alimentos")
    print(f"│  {len(grupos):>7}  categorías: {', '.join(grupos[:6])}…")
    print(f"│  {con_micros:>7}  con micronutrientes")
    print(f"│  {con_marca:>7}  con marca")
    print(f"│  {con_momento:>7}  con momento sugerido")
    print("╰──────────────────────────────────────────────────────────────")

    if avisos:
        print(f"\nAvisos del CSV ({len(avisos)}):")
        for a in avisos[:25]:
            print(f"  · {a}")
        if len(avisos) > 25:
            print(f"  · … y {len(avisos) - 25} más")


# ── Ejecutar ───────────────────────────────────────────────────────────────

def limpiar(db, patrones):
    from datetime import datetime

    for tabla, col, _rotulo in DESVINCULAR:
        if _existe(db, tabla):
            db.execute(text(f"UPDATE {tabla} SET {col} = NULL WHERE {col} IS NOT NULL"))
    for tabla, _rotulo in BORRADOS:
        if _existe(db, tabla):
            db.execute(text(f"DELETE FROM {tabla}"))
    n = 0
    for detalle_id, _email in usuarios_de_prueba(db, patrones):
        # La fecha se pasa desde Python: `NOW()` no existe en SQLite y esto
        # también corre contra la base de pruebas.
        db.execute(text("UPDATE user_details SET deleted_at = :t WHERE id = :i"),
                   {"i": detalle_id, "t": datetime.utcnow()})
        n += 1
    return n


def cargar(db, alimentos, organization_id, usuario_id):
    """Crea las categorías que falten y mete los alimentos."""
    import uuid as _uuid
    from datetime import datetime

    grupos = {}
    for fila in db.execute(text("SELECT id, name FROM group_foods")).fetchall():
        grupos[_clave(fila[1])] = fila[0]

    creadas = 0
    for nombre in sorted({a["grupo"] for a in alimentos if a["grupo"]}):
        if _clave(nombre) not in grupos:
            db.execute(text(
                "INSERT INTO group_foods (name, status, created_at, updated_at) "
                "VALUES (:n, 1, :t, :t)"), {"n": nombre, "t": datetime.utcnow()})
            grupos[_clave(nombre)] = db.execute(
                text("SELECT id FROM group_foods WHERE name = :n"), {"n": nombre}).scalar()
            creadas += 1

    ahora = datetime.utcnow()
    for a in alimentos:
        aid = str(_uuid.uuid4())
        db.execute(text(
            "INSERT INTO aliments (id, group_food_id, brand, name, quantity, quantity_unit,"
            " proteins, carbohydrates, fats, calories, comments, meal_moments,"
            " organization_id, created_user_id, created_at, updated_at) "
            "VALUES (:id, :g, :marca, :nombre, :cant, :uni, :p, :c, :gr, :k, :com, :mom,"
            " :org, :usr, :t, :t)"), {
            "id": aid, "g": grupos.get(_clave(a["grupo"] or "")), "marca": a["marca"],
            "nombre": a["nombre"], "cant": a["cantidad"], "uni": a["unidad"],
            "p": a["proteinas"], "c": a["carbohidratos"], "gr": a["grasas"],
            "k": a["calorias"], "com": a["comments"], "mom": a["momento"],
            "org": organization_id, "usr": usuario_id, "t": ahora})

        if a["micros"]:
            cols = ", ".join(a["micros"].keys())
            vals = ", ".join(f":{c}" for c in a["micros"])
            db.execute(text(
                f"INSERT INTO aliment_descriptions (aliment_id, {cols}) "
                f"VALUES (:aid, {vals})"), {"aid": aid, **a["micros"]})
    return creadas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", required=True, help="El CSV de alimentos")
    ap.add_argument("--ejecutar", action="store_true",
                    help="Escribir de verdad. Sin esto solo cuenta.")
    ap.add_argument("--organizacion", default=None,
                    help="Id de la organización dueña. Sin esto, catálogo común.")
    ap.add_argument("--usuario", type=int, default=None,
                    help="Id del usuario que consta como creador.")
    ap.add_argument("--verificar", action="store_true",
                    help="Comprobar cómo quedó la base después de cargar.")
    ap.add_argument("--inspeccionar", action="store_true",
                    help="Solo mirar qué hay en la base. No toca nada.")
    ap.add_argument("--patron-prueba", action="append", default=None,
                    help="Patrón SQL de correos de prueba. Se puede repetir.")
    args = ap.parse_args()

    # Sin esto la aplicación se cae a una base local por defecto, y un script
    # que borra no puede adivinar contra qué trabaja.
    if not (os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")):
        print("Falta DATABASE_URL: no está claro contra qué base se trabajaría.",
              file=sys.stderr)
        print('  PowerShell: $env:DATABASE_URL="mysql+pymysql://..."', file=sys.stderr)
        print('  Mac/Linux:  export DATABASE_URL="mysql+pymysql://..."', file=sys.stderr)
        return 1

    patrones = args.patron_prueba or PATRONES_PRUEBA
    alimentos, avisos = leer_csv(args.csv)

    db = SessionLocal()
    try:
        # Antes de cualquier cuenta: si no se llega a la base, hay que decirlo
        # con esas palabras y parar.
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            print(f"\nNo se ha podido conectar a {_contra_que_base()}", file=sys.stderr)
            detalle = str(e).split("\n")[0]
            print(f"  {detalle}", file=sys.stderr)
            if "access denied" in detalle.lower():
                print("\n  La contraseña no es válida. Revisa que hayas pegado la de",
                      file=sys.stderr)
                print("  verdad: en Railway, servicio MySQL -> Variables ->",
                      file=sys.stderr)
                print("  MYSQL_PUBLIC_URL.", file=sys.stderr)
            print("\n  No se ha leído ni tocado nada.\n", file=sys.stderr)
            return 1

        if args.verificar:
            return verificar(db, alimentos)

        if args.inspeccionar:
            inspeccionar(db, alimentos)
            return 0

        informe(db, alimentos, avisos, patrones)

        if not args.ejecutar:
            print("\nSIMULACRO: no se ha tocado nada.")
            print("Cuando los números cuadren, repite con --ejecutar.")
            print("Antes: copia de seguridad. Esto no se deshace.\n")
            return

        print(f"\nEjecutando sobre {_contra_que_base()} …")
        bajas = limpiar(db, patrones)
        creadas = cargar(db, alimentos, args.organizacion, args.usuario)
        db.commit()
        print(f"  · {bajas} usuarios de prueba dados de baja")
        print(f"  · {creadas} categorías nuevas")
        print(f"  · {len(alimentos)} alimentos cargados")
        print("Hecho.\n")
    except Exception:
        db.rollback()
        # Solo tiene sentido decirlo si se estaba escribiendo. En un simulacro o
        # una verificación no había nada que guardar, y el mensaje confunde.
        if args.ejecutar:
            print("\nERROR: no se ha guardado nada, la base queda como estaba.\n",
                  file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Con `main()` a secas el código de salida era SIEMPRE 0: una verificación
    # fallida, o una URL de base sin poner, parecían correctas para cualquier
    # cosa que llamara al script.
    sys.exit(main() or 0)
