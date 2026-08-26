"""Subtítulo en las comidas de una dieta

El nombre de la comida dice CUÁNDO se come ("Desayuno", "Cena") y se repite
igual en todas las dietas. Lo que se come no estaba en ninguna parte: el
cliente tenía que abrir la comida y leer la lista de alimentos para saber qué
le tocaba.

Revision ID: b8c9d0e1f2a3
Revises: a7c8h9a0t1a2
"""
import sqlalchemy as sa
from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7c8h9a0t1a2"
branch_labels = None
depends_on = None


def _columnas(bind):
    return {c["name"] for c in sa.inspect(bind).get_columns("diet_foods")}


def upgrade():
    bind = op.get_bind()
    if "subtitle" not in _columnas(bind):
        op.add_column("diet_foods", sa.Column("subtitle", sa.String(255), nullable=True))


def downgrade():
    bind = op.get_bind()
    if "subtitle" in _columnas(bind):
        op.drop_column("diet_foods", "subtitle")
