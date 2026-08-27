"""Copia de seguridad de los datos, en Python puro.

Existe porque las otras dos vías no estaban disponibles: las copias de Railway
piden plan Pro, y `mysqldump` no viene con Python y en Windows hay que instalar
MySQL entero para tenerlo. Esto usa lo que ya está instalado para hacer correr
la aplicación.

Vuelca los DATOS, no la estructura: las tablas las crea Alembic al desplegar.
Para lo que hace falta aquí —poder devolver la base a como estaba si el borrado
sale mal— con los datos basta.

Y comprueba lo que escribe. Que el fichero exista no significa nada: uno
cortado a la mitad pesa lo suyo y parece correcto hasta el día que hace falta
restaurarlo, que es el peor día para descubrirlo.

    python scripts/copia_seguridad.py
    python scripts/copia_seguridad.py --restaurar copia-20260826-2130.sql

La conexión sale de DATABASE_URL.
"""
import argparse
import os
import sys
from datetime import date, datetime, time
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text                            # noqa: E402

from app.database import SessionLocal, engine                   # noqa: E402

# Marca del final. Si no está, el volcado se cortó: es la única señal fiable de
# que llegó hasta el final y no se quedó a medias.
FIN = "-- FIN DE LA COPIA --"

# `alembic_version` NO se copia: dice por qué migración va la base, y eso lo
# lleva Alembic al desplegar. Restaurarlo choca con la fila que ya hay y, si
# colara, dejaría a la base creyéndose en otra versión de la que tiene.
SIN_COPIAR = {"alembic_version"}


def _sql(v, motor="mysql"):
    """Un valor, como literal de SQL.

    Cada motor escapa distinto y esto se equivocaba: MySQL admite `\\'` para el
    apóstrofo y SQLite no —ahí hay que doblarlo—. Un nombre como "Aceite
    d'oliva" partía la sentencia en dos y el fichero entero dejaba de poder
    restaurarse, no solo esa fila.
    """
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    # `datetime` va PRIMERO: es subclase de `date`, y al revés una fecha suelta
    # entraría por aquí y `date.isoformat()` no admite `sep`. Se me pasó porque
    # las tablas con fechas sueltas —check-ins, sesiones— estaban vacías en las
    # pruebas, así que ninguna fila llegaba a esta línea.
    if isinstance(v, datetime):
        return "'" + v.isoformat(sep=" ") + "'"
    if isinstance(v, (date, time)):
        return "'" + v.isoformat() + "'"
    if isinstance(v, (bytes, bytearray)):
        return "0x" + v.hex()

    s = str(v)
    # Doblar el apóstrofo vale en los dos. La barra invertida solo es un
    # escape en MySQL; en SQLite es un carácter normal y tocarla la duplicaría.
    if motor == "mysql":
        s = s.replace("\\", "\\\\")
    s = s.replace("'", "''")

    # Cada fila va en una línea, así que los saltos no pueden ir tal cual: la
    # restauración lee línea a línea y partiría la sentencia por la mitad.
    if "\n" in s or "\r" in s:
        if motor == "mysql":
            s = s.replace("\r", "\\r").replace("\n", "\\n")
        else:
            # SQLite no tiene escapes: se parte el texto y se pega con char().
            for crudo, codigo in (("\r", "13"), ("\n", "10")):
                s = s.replace(crudo, f"' || char({codigo}) || '")
    return "'" + s + "'"


def _upsert(motor, tabla, cols):
    """La forma de «mete la fila, y si ya está, písala», según el motor.

    Se hace con UPSERT y no con REPLACE aunque REPLACE valga en los dos: en
    MySQL, REPLACE borra la fila antes de meterla, y ese borrado dispara los
    ON DELETE CASCADE. Restaurando `aliments` se llevaría por delante los
    `aliment_descriptions` que ya se hubieran metido — la copia destruyendo
    parte de lo que venía a salvar.
    """
    lista = ", ".join(f"`{c}`" for c in cols) if motor == "mysql" \
        else ", ".join(f'"{c}"' for c in cols)
    if motor == "mysql":
        pisa = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in cols)
        return f"INSERT INTO `{tabla}` ({lista}) VALUES ({{v}}) ON DUPLICATE KEY UPDATE {pisa};"
    pisa = ", ".join(f'"{c}"=excluded."{c}"' for c in cols)
    return (f'INSERT INTO "{tabla}" ({lista}) VALUES ({{v}}) '
            f'ON CONFLICT DO UPDATE SET {pisa};')


def volcar(destino):
    motor = engine.dialect.name
    insp = inspect(engine)
    tablas = [t for t in sorted(insp.get_table_names()) if t not in SIN_COPIAR]
    db = SessionLocal()
    filas_totales = 0
    conteos = {}
    try:
        with open(destino, "w", encoding="utf-8") as fh:
            fh.write("-- Copia de NutriEntrena\n")
            fh.write(f"-- {datetime.utcnow().isoformat(sep=' ')} UTC\n")
            fh.write("-- Solo datos: la estructura la crea Alembic al desplegar.\n\n")
            # Las filas se escriben por orden alfabético de tabla, que no es
            # el orden de las dependencias: sin apagar las claves ajenas, meter
            # un hijo antes que su padre falla.
            if motor == "mysql":
                fh.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

            for t in tablas:
                cols = [c["name"] for c in insp.get_columns(t)]
                if not cols:
                    continue
                filas = db.execute(text(f"SELECT * FROM `{t}`")).fetchall()
                conteos[t] = len(filas)
                filas_totales += len(filas)
                if not filas:
                    continue
                # Si la fila sigue estando, se pisa con la de la copia. Un
                # INSERT a secas revienta con "Duplicate entry" en cuanto una
                # tabla no se hubiera vaciado, y la restauración se queda a
                # medias, que es peor que no haberla intentado.
                plantilla = _upsert(motor, t, cols)
                fh.write(f"-- {t}: {len(filas)} filas\n")
                for fila in filas:
                    fh.write(plantilla.format(v=", ".join(_sql(v, motor) for v in fila)) + "\n")
                fh.write("\n")

            if motor == "mysql":
                fh.write("SET FOREIGN_KEY_CHECKS=1;\n")
            fh.write(FIN + "\n")
    finally:
        db.close()
    return tablas, conteos, filas_totales


def comprobar(destino, filas_esperadas):
    """Que el fichero sirva, no solo que exista."""
    with open(destino, encoding="utf-8") as fh:
        contenido = fh.read()
    if not contenido.rstrip().endswith(FIN):
        return "el volcado está incompleto, le falta la marca del final"
    escritas = contenido.count("\nINSERT INTO ")
    if escritas != filas_esperadas:
        return f"se esperaban {filas_esperadas} filas y hay {escritas} en el fichero"
    return None


def restaurar(origen):
    with open(origen, encoding="utf-8") as fh:
        contenido = fh.read()
    if not contenido.rstrip().endswith(FIN):
        print("Ese fichero está incompleto. No se restaura nada.", file=sys.stderr)
        return 1
    db = SessionLocal()
    hechas = 0
    try:
        # En SQLite las claves ajenas se apagan por conexión, no con SQL dentro
        # del fichero.
        if engine.dialect.name == "sqlite":
            db.execute(text("PRAGMA foreign_keys=OFF"))
        for linea in contenido.splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("--"):
                continue
            db.execute(text(linea.rstrip(";")))
            hechas += 1
        db.commit()
        print(f"Restauradas {hechas} sentencias.")
        return 0
    except Exception:
        db.rollback()
        print("ERROR al restaurar: no se ha guardado nada.", file=sys.stderr)
        raise
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--restaurar", metavar="FICHERO",
                    help="Volver a meter una copia en la base de datos.")
    ap.add_argument("--salida", default=None, help="Nombre del fichero.")
    args = ap.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("Falta DATABASE_URL.", file=sys.stderr)
        print('  PowerShell: $env:DATABASE_URL="mysql+pymysql://..."', file=sys.stderr)
        print('  Mac/Linux:  export DATABASE_URL="mysql+pymysql://..."', file=sys.stderr)
        return 1

    if args.restaurar:
        return restaurar(args.restaurar)

    destino = args.salida or f"copia-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sql"
    print(f"Volcando a {destino} …")
    tablas, conteos, total = volcar(destino)

    problema = comprobar(destino, total)
    print()
    print(f"  fichero: {destino}")
    print(f"  peso:    {os.path.getsize(destino) // 1024} KB")
    print(f"  tablas:  {len(tablas)}")
    print(f"  filas:   {total}")
    print()
    print("  Lo más gordo:")
    for t, n in sorted(conteos.items(), key=lambda kv: -kv[1])[:8]:
        if n:
            print(f"    {n:>7}  {t}")

    if problema:
        print(f"\nMAL: {problema}", file=sys.stderr)
        print("NO sirve como copia. No sigas con el borrado.", file=sys.stderr)
        return 1

    print("\nLa copia está completa y cuadra.")
    print(f"Guárdala fuera de Railway. Para volver atrás: "
          f"python scripts/copia_seguridad.py --restaurar {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
