"""add sugars to aliment_descriptions

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'c6d7e8f9a0b1'
down_revision = 'b5c6d7e8f9a0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('aliment_descriptions', sa.Column('sugars', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('aliment_descriptions', 'sugars')
