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


def _cuenta(db, tabla, donde=""):
    try:
        return db.execute(text(f"SELECT COUNT(*) FROM {tabla} {donde}")).scalar() or 0
    except Exception:
        return None      # la tabla puede no existir en una base vieja


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
        print("├─ DE DÓNDE SALEN LOS ALIMENTOS DE AHORA ──────────────────────")
        print(f"│  {total_al:>7}  en la base")
        print(f"│  {copias:>7}  copias de otro alimento (se clonan al asignar dietas)")
        print(f"│  {total_al - copias:>7}  originales")
        print(f"│  {de_org:>7}  de alguna cuenta; {total_al - de_org} del catálogo común")
        if total_al > len(alimentos) * 1.5:
            print("│")
            print(f"│  OJO: el CSV trae {len(alimentos)} y en la base hay {total_al}.")
            print("│  Vaciar y cargar PIERDE la diferencia. Mira el desglose de")
            print("│  arriba antes de seguir.")

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
    ap.add_argument("--patron-prueba", action="append", default=None,
                    help="Patrón SQL de correos de prueba. Se puede repetir.")
    args = ap.parse_args()

    patrones = args.patron_prueba or PATRONES_PRUEBA
    alimentos, avisos = leer_csv(args.csv)

    db = SessionLocal()
    try:
        informe(db, alimentos, avisos, patrones)

        if not args.ejecutar:
            print("\nSIMULACRO: no se ha tocado nada.")
            print("Cuando los números cuadren, repite con --ejecutar.")
            print("Antes: copia de seguridad. Esto no se deshace.\n")
            return

        print("\nEjecutando…")
        bajas = limpiar(db, patrones)
        creadas = cargar(db, alimentos, args.organizacion, args.usuario)
        db.commit()
        print(f"  · {bajas} usuarios de prueba dados de baja")
        print(f"  · {creadas} categorías nuevas")
        print(f"  · {len(alimentos)} alimentos cargados")
        print("Hecho.\n")
    except Exception:
        db.rollback()
        print("\nERROR: no se ha guardado nada, la base queda como estaba.\n")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
