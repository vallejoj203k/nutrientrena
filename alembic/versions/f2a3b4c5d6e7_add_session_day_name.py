"""El día de la rutina en la sesión registrada

El historial enseña "Día 4 · Pierna · Femoral y glúteo". Con solo `routine_id`
la columna diría el nombre de la rutina entera, que es el mismo texto en las
cincuenta filas y no dice nada.

Se guarda como copia, igual que el nombre de los ejercicios de la sesión: el
historial tiene que seguir leyéndose aunque la rutina se renombre o se borre.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""
import sqlalchemy as sa
from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def _columnas(bind):
    return {c["name"] for c in sa.inspect(bind).get_columns("workout_sessions")}


def upgrade():
    bind = op.get_bind()
    if "day_name" not in _columnas(bind):
        op.add_column("workout_sessions", sa.Column("day_name", sa.String(255), nullable=True))


def downgrade():
    bind = op.get_bind()
    if "day_name" in _columnas(bind):
        op.drop_column("workout_sessions", "day_name")
