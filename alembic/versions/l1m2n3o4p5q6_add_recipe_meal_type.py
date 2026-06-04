"""add recipe meal_type

Revision ID: l1m2n3o4p5q6
Revises: k0l1m2n3o4p5
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'l1m2n3o4p5q6'
down_revision = 'k0l1m2n3o4p5'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('recipes')]
    if 'meal_type' not in cols:
        op.add_column('recipes', sa.Column('meal_type', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('recipes', 'meal_type')
