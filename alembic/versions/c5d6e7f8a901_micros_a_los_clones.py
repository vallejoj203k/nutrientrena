"""La ficha de micronutrientes, también en los alimentos de las dietas

Meter un alimento en una dieta hace una copia suya (con `parent_id` al del
catálogo). La copia llevaba los macros pero no la ficha de micronutrientes,
donde vive la fibra: en el editor, toda dieta salía con 0 g de fibra en cada
alimento aunque el del catálogo la tuviera.

Las copias nuevas ya la llevan. Esta migración se la da a las que ya existen,
copiándola de su alimento padre. Solo a las que no tienen ninguna: una copia
con ficha propia es que alguien la editó, y no se pisa.

Revision ID: c5d6e7f8a901
Revises: b4c5d6e7f809
"""
import sqlalchemy as sa
from alembic import op

revision = "c5d6e7f8a901"
down_revision = "b4c5d6e7f809"
branch_labels = None
depends_on = None


def copiar_micros_a_los_clones(bind) -> int:
    """Devuelve cuántas copias han recibido ficha."""
    insp = sa.inspect(bind)
    if "aliment_descriptions" not in insp.get_table_names():
        return 0
    cols = [c["name"] for c in insp.get_columns("aliment_descriptions")
            if c["name"] not in ("id", "aliment_id")]
    lista = ", ".join(cols)
    de_padre = ", ".join(f"p.{c}" for c in cols)
    r = bind.execute(sa.text(f"""
        INSERT INTO aliment_descriptions (aliment_id, {lista})
        SELECT c.id, {de_padre}
        FROM aliments c
        JOIN aliment_descriptions p ON p.aliment_id = c.parent_id
        WHERE c.parent_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM aliment_descriptions x WHERE x.aliment_id = c.id)
    """))
    return r.rowcount or 0


def upgrade():
    copiar_micros_a_los_clones(op.get_bind())


def downgrade():
    # Las fichas copiadas no se distinguen de las escritas a mano: se dejan.
    pass
