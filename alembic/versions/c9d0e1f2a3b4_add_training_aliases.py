"""Otros nombres (sinónimos) de un ejercicio

Un mismo ejercicio se llama de varias formas: "Press de banca", "bench press",
"press banca plano". El catálogo solo guardaba uno, así que quien buscaba por
cualquiera de los otros no encontraba nada y acababa creando un duplicado.

Se guardan separados por comas y solo intervienen en la BÚSQUEDA: el nombre con
el que se muestra el ejercicio sigue siendo `name`.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""
import sqlalchemy as sa
from alembic import op

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def _columnas(bind):
    return {c["name"] for c in sa.inspect(bind).get_columns("trainings")}


def upgrade():
    bind = op.get_bind()
    if "aliases" not in _columnas(bind):
        op.add_column("trainings", sa.Column("aliases", sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    if "aliases" in _columnas(bind):
        op.drop_column("trainings", "aliases")
