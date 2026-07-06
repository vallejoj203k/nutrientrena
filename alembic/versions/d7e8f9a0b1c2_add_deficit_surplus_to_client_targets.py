"""add deficit/surplus to client_targets

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'd7e8f9a0b1c2'
down_revision = 'c6d7e8f9a0b1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('client_targets', sa.Column('deficit', sa.Float(), nullable=True))
    op.add_column('client_targets', sa.Column('surplus', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('client_targets', 'deficit')
    op.drop_column('client_targets', 'surplus')
