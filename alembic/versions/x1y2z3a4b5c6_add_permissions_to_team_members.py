"""Add permissions column to team_members

Revision ID: x1y2z3a4b5c6
Revises: w1x2y3z4a5b6
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'x1y2z3a4b5c6'
down_revision = 'w1x2y3z4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('team_members', sa.Column('permissions', sa.Text(), nullable=True))
    op.add_column('team_members', sa.Column('variable_type', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('team_members', 'variable_type')
    op.drop_column('team_members', 'permissions')
