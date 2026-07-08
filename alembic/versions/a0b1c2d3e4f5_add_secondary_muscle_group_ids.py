"""add secondary_muscle_group_ids to trainings

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = 'a0b1c2d3e4f5'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('trainings', sa.Column('secondary_muscle_group_ids', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('trainings', 'secondary_muscle_group_ids')
