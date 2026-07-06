"""add age and body_fat to user_details

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'e8f9a0b1c2d3'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_details', sa.Column('age', sa.Integer(), nullable=True))
    op.add_column('user_details', sa.Column('body_fat', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('user_details', 'age')
    op.drop_column('user_details', 'body_fat')
