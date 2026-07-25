"""add requirements (JSON) a calendar_tasks

Guarda de forma estructurada qué se le pide al cliente en cada tarea
(peso/medidas/fotos, formulario, rutina, dieta, documento), de modo que la
zona del cliente pueda mostrarlo y marcarlo como cumplido.

Revision ID: f5e6f7a8b9c0
Revises: f4d5e6f7a8b9
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'f5e6f7a8b9c0'
down_revision = 'f4d5e6f7a8b9'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('calendar_tasks', 'requirements'):
        op.add_column('calendar_tasks', sa.Column('requirements', sa.Text(), nullable=True))


def downgrade():
    if _has_column('calendar_tasks', 'requirements'):
        op.drop_column('calendar_tasks', 'requirements')
