"""add meal_moments a aliments

En qué momentos del día encaja cada alimento (desayuno, snack, principal).
Sin esto el generador solo mira macros y puede proponer carne de vacuno para
desayunar: cuadra las calorías pero no es un desayuno.

Vacío = el generador lo deduce del nombre; rellenarlo es la forma que tiene
el coach de corregir esa deducción.

Revision ID: fa0e1f2a3b4c
Revises: f9d0e1f2a3b4
Create Date: 2026-07-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'fa0e1f2a3b4c'
down_revision = 'f9d0e1f2a3b4'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('aliments', 'meal_moments'):
        op.add_column('aliments', sa.Column('meal_moments', sa.String(60), nullable=True))


def downgrade():
    if _has_column('aliments', 'meal_moments'):
        op.drop_column('aliments', 'meal_moments')
