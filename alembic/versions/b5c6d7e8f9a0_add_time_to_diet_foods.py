"""add time field to diet_foods

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'b5c6d7e8f9a0'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('diet_foods', sa.Column('time', sa.String(10), nullable=True))


def downgrade():
    op.drop_column('diet_foods', 'time')
