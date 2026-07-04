"""add content text field to routine_blocks

Revision ID: a4b5c6d7e8f9
Revises: z3a4b5c6d7e8
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'a4b5c6d7e8f9'
down_revision = 'z3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('routine_blocks', sa.Column('content', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('routine_blocks', 'content')
