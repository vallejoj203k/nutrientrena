"""Add photo column to team_members

Revision ID: ab2bc3cd4de5
Revises: aa1bb2cc3dd4
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'ab2bc3cd4de5'
down_revision = 'aa1bb2cc3dd4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('team_members', sa.Column('photo', sa.String(2048), nullable=True))


def downgrade():
    op.drop_column('team_members', 'photo')
