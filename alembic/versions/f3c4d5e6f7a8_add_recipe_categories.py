"""add categories to recipes (tipo de dieta múltiple)

Revision ID: f3c4d5e6f7a8
Revises: f2b3c4d5e6f7
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3c4d5e6f7a8'
down_revision = 'f2b3c4d5e6f7'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        return column in [c['name'] for c in insp.get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('recipes', 'categories'):
        op.add_column('recipes', sa.Column('categories', sa.String(255), nullable=True))


def downgrade():
    if _has_column('recipes', 'categories'):
        op.drop_column('recipes', 'categories')
