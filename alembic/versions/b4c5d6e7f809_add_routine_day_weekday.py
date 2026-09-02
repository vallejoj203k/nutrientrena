"""Qué día de la semana toca cada día de la rutina

Hasta ahora se deducía del orden: el primer día era el lunes, el segundo el
martes, y así. Eso no sabe decir "los miércoles descanso": con cuatro días de
entreno salían lunes, martes, miércoles y jueves, aunque el coach los hubiera
pensado para lunes, martes, jueves y viernes.

Nulo significa "sin día asignado", que es lo que tienen todas las rutinas que
ya existen: no se les inventa un reparto que nadie decidió.

Revision ID: b4c5d6e7f809
Revises: a3b4c5d6e7f8
"""
import sqlalchemy as sa
from alembic import op

revision = "b4c5d6e7f809"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def _columnas(bind):
    return {c["name"] for c in sa.inspect(bind).get_columns("routine_days")}


def upgrade():
    bind = op.get_bind()
    if "weekday" not in _columnas(bind):
        # 0 = lunes … 6 = domingo. Nulo = sin asignar.
        op.add_column("routine_days", sa.Column("weekday", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    if "weekday" in _columnas(bind):
        op.drop_column("routine_days", "weekday")
