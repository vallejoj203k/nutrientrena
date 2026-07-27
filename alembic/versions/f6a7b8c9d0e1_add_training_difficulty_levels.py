"""add difficulty_levels a trainings

Un ejercicio puede ser apto para varios niveles (principiante, intermedio y
avanzado a la vez). Se guardan separados por coma; `difficulty` conserva el
nivel más bajo para no romper filtros ni lecturas antiguas.

Revision ID: f6a7b8c9d0e1
Revises: f5e6f7a8b9c0
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'f5e6f7a8b9c0'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('trainings', 'difficulty_levels'):
        op.add_column('trainings', sa.Column('difficulty_levels', sa.Text(), nullable=True))
        # Los ejercicios existentes conservan su único nivel.
        op.execute(
            "UPDATE trainings SET difficulty_levels = CAST(difficulty AS CHAR) "
            "WHERE difficulty IS NOT NULL AND difficulty_levels IS NULL"
        )


def downgrade():
    if _has_column('trainings', 'difficulty_levels'):
        op.drop_column('trainings', 'difficulty_levels')
