"""add photo to user_details

Revision ID: p4q5r6s7t8u9
Revises: o3p4q5r6s7t8
Create Date: 2026-06-17

"""
from alembic import op
import sqlalchemy as sa

revision = 'p4q5r6s7t8u9'
down_revision = 'o3p4q5r6s7t8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_details', sa.Column('photo', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('user_details', 'photo')
