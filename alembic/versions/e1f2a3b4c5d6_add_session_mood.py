"""Cómo se ha sentido el cliente al terminar el entreno

La ficha de sesiones lo enseña como una cara. No se derivaba del RPE a
propósito: el esfuerzo percibido y el ánimo no son lo mismo, y una cara
calculada del RPE sería un dato que el cliente nunca dio.

De 1 (fatal) a 5 (genial). Opcional: las sesiones ya registradas se quedan sin
cara, y ahí la columna sale vacía en vez de inventarse un "normal".

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""
import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def _columnas(bind):
    return {c["name"] for c in sa.inspect(bind).get_columns("workout_sessions")}


def upgrade():
    bind = op.get_bind()
    if "mood" not in _columnas(bind):
        op.add_column("workout_sessions", sa.Column("mood", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    if "mood" in _columnas(bind):
        op.drop_column("workout_sessions", "mood")
