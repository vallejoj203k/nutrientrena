"""add deleted_at a user_details

Baja reversible de clientes, coaches y miembros del equipo: el usuario deja de
aparecer en los listados y no puede iniciar sesión, pero se conserva todo su
historial (dietas, rutinas, check-ins, chat…), que cuelga de users.id en
decenas de tablas.

Revision ID: f8c9d0e1f2a3
Revises: f7b8c9d0e1f2
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'f8c9d0e1f2a3'
down_revision = 'f7b8c9d0e1f2'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('user_details', 'deleted_at'):
        op.add_column('user_details', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade():
    if _has_column('user_details', 'deleted_at'):
        op.drop_column('user_details', 'deleted_at')
