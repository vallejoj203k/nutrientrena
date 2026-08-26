"""La copia de seguridad de los datos.

Existe porque las otras vías no estaban disponibles: las copias de Railway
piden plan Pro y `mysqldump` no viene con Python.

Una copia solo vale si se puede RESTAURAR, así que eso es lo que se comprueba:
se vuelca, se borra, se restaura y se mira si volvió. Comprobar que el fichero
existe no dice nada — uno cortado a la mitad pesa lo suyo y parece correcto
hasta el día que hace falta, que es el peor día para descubrirlo.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.group_food import GroupFood

from scripts.copia_seguridad import FIN, SIN_COPIAR, _sql, comprobar, restaurar, volcar


def _sesion():
    return SessionLocal()


# ── Escapar valores, que es donde un volcado casero se rompe ───────────────

def test_UN_APOSTROFO_NO_PARTE_LA_SENTENCIA():
    """"Aceite d'oliva" partiría el INSERT en dos y dejaría el fichero entero
    sin poder restaurarse, no solo esa fila. Doblarlo vale en los dos motores.
    """
    assert _sql("Aceite d'oliva", "mysql") == "'Aceite d''oliva'"
    assert _sql("Aceite d'oliva", "sqlite") == "'Aceite d''oliva'"


def test_la_barra_invertida_solo_se_escapa_en_mysql():
    """En SQLite es un carácter normal: escaparla la duplicaría de verdad."""
    assert _sql("con \\ barra", "mysql") == "'con \\\\ barra'"
    assert _sql("con \\ barra", "sqlite") == "'con \\ barra'"


def test_los_saltos_de_linea_no_parten_la_fila():
    """Cada fila va en una línea y la restauración lee línea a línea."""
    assert "\n" not in _sql("línea1\nlínea2", "mysql")[1:-1].replace("\\n", "")
    assert "\n" not in _sql("línea1\nlínea2", "sqlite")


def test_los_vacios_van_como_NULL_no_como_texto():
    """`None` escrito como 'None' convertiría un hueco en la palabra."""
    assert _sql(None) == "NULL"
    assert _sql(0) == "0"
    assert _sql(False) == "0"


# ── Volcar y restaurar de verdad ───────────────────────────────────────────

def test_LA_COPIA_SE_PUEDE_RESTAURAR(client, seed, admin_headers, tmp_path):
    """Lo único que demuestra que una copia sirve."""
    suf = uuid.uuid4().hex[:8]
    db = _sesion()
    try:
        g = GroupFood(name=f"Aceites {suf}")
        db.add(g)
        db.flush()
        db.add(Aliment(id=str(uuid.uuid4()), group_food_id=g.id,
                       name=f"Aceite d'oliva \"virgen\" {suf}", brand="Hacendado",
                       calories=819.0, quantity=100.0, quantity_unit="g",
                       comments="línea1\nlínea2 con \\ barra"))
        db.commit()
        antes = db.query(Aliment).count()
    finally:
        db.close()

    destino = str(tmp_path / "copia.sql")
    _tablas, _conteos, total = volcar(destino)
    assert comprobar(destino, total) is None, comprobar(destino, total)

    # Se borra lo mismo que borraría el vaciado del catálogo.
    db = _sesion()
    try:
        db.query(Aliment).delete()
        db.commit()
        assert db.query(Aliment).count() == 0
    finally:
        db.close()

    assert restaurar(destino) == 0

    db = _sesion()
    try:
        assert db.query(Aliment).count() == antes, "no ha vuelto todo"
        al = db.query(Aliment).filter(Aliment.name.like(f"%{suf}%")).first()
        # Los caracteres que rompen un volcado mal escrito.
        assert al.name == f"Aceite d'oliva \"virgen\" {suf}", al.name
        assert al.comments == "línea1\nlínea2 con \\ barra", repr(al.comments)
    finally:
        db.close()


def test_RESTAURAR_DOS_VECES_NO_DUPLICA_NADA(client, seed, admin_headers, tmp_path):
    """Se restaura sobre una base que no se vació del todo, o dos veces por
    nervios. Con un INSERT a secas eso revienta con "Duplicate entry" y la
    restauración se queda a medias, que es peor que no haberla intentado."""
    destino = str(tmp_path / "copia.sql")
    _t, _c, _total = volcar(destino)

    assert restaurar(destino) == 0
    db = _sesion()
    try:
        una_vez = db.query(Aliment).count()
    finally:
        db.close()

    assert restaurar(destino) == 0
    db = _sesion()
    try:
        assert db.query(Aliment).count() == una_vez
    finally:
        db.close()


def test_UN_FICHERO_CORTADO_NO_SE_RESTAURA(client, seed, admin_headers, tmp_path):
    """Media copia metida en la base es peor que ninguna: deja los datos en un
    estado que nadie ha visto nunca."""
    destino = tmp_path / "copia.sql"
    _t, _c, _total = volcar(str(destino))
    entero = destino.read_text(encoding="utf-8")
    destino.write_text(entero[:len(entero) // 2], encoding="utf-8")

    assert restaurar(str(destino)) == 1
    assert comprobar(str(destino), 999) is not None


def test_la_comprobacion_cuenta_las_filas(client, seed, admin_headers, tmp_path):
    """Que acabe bien no basta: si faltan filas por el camino, la copia no es
    la base de datos."""
    destino = str(tmp_path / "copia.sql")
    _t, _c, total = volcar(destino)
    assert comprobar(destino, total) is None
    assert "se esperaban" in comprobar(destino, total + 1)


def test_NO_SE_COPIA_LA_VERSION_DE_ALEMBIC(client, seed, admin_headers, tmp_path):
    """Dice por qué migración va la base, y eso lo lleva Alembic al desplegar.
    Restaurarlo dejaría a la base creyéndose en otra versión de la que tiene.
    """
    assert "alembic_version" in SIN_COPIAR
    destino = tmp_path / "copia.sql"
    tablas, _c, _t = volcar(str(destino))
    assert "alembic_version" not in tablas
    assert "alembic_version" not in destino.read_text(encoding="utf-8")


def test_la_copia_lleva_su_marca_de_final(client, seed, admin_headers, tmp_path):
    destino = tmp_path / "copia.sql"
    volcar(str(destino))
    assert destino.read_text(encoding="utf-8").rstrip().endswith(FIN)
