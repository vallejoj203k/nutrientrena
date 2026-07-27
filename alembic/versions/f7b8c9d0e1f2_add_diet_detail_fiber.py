"""add fiber a diet_details

Objetivo de fibra (g/día) de la plantilla, junto a proteínas, carbos y grasas.

Revision ID: f7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('diet_details', 'fiber'):
        op.add_column('diet_details', sa.Column('fiber', sa.Float(), nullable=True))


def downgrade():
    if _has_column('diet_details', 'fiber'):
        op.drop_column('diet_details', 'fiber')
