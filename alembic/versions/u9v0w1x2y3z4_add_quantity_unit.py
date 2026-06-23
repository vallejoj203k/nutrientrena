"""add quantity_unit to aliments and client_aliments

Revision ID: u9v0w1x2y3z4
Revises: t8u9v0w1x2y3
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = 'u9v0w1x2y3z4'
down_revision = 't8u9v0w1x2y3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('aliments', sa.Column('quantity_unit', sa.String(20), nullable=True))
    op.add_column('client_aliments', sa.Column('quantity_unit', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('aliments', 'quantity_unit')
    op.drop_column('client_aliments', 'quantity_unit')
