"""Add currency column to team_members

Revision ID: y2z3a4b5c6d7
Revises: x1y2z3a4b5c6
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'y2z3a4b5c6d7'
down_revision = 'x1y2z3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('team_members', sa.Column('currency', sa.String(10), nullable=True, server_default='EUR'))


def downgrade():
    op.drop_column('team_members', 'currency')
