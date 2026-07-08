"""add restrictions and preferences to user_details

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'f9a0b1c2d3e4'
down_revision = 'e8f9a0b1c2d3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_details', sa.Column('allergies', sa.Text(), nullable=True))
    op.add_column('user_details', sa.Column('intolerances', sa.Text(), nullable=True))
    op.add_column('user_details', sa.Column('dislikes', sa.Text(), nullable=True))
    op.add_column('user_details', sa.Column('injuries', sa.Text(), nullable=True))
    op.add_column('user_details', sa.Column('equipment', sa.Text(), nullable=True))
    op.add_column('user_details', sa.Column('food_preferences', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('user_details', 'food_preferences')
    op.drop_column('user_details', 'equipment')
    op.drop_column('user_details', 'injuries')
    op.drop_column('user_details', 'dislikes')
    op.drop_column('user_details', 'intolerances')
    op.drop_column('user_details', 'allergies')
