"""add chat_enabled to user_details

Adds a per-client chat_enabled flag so the coach can enable/disable the
client's chat from the profile. Existing rows are backfilled to enabled.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'e4f5a6b7c8d9'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user_details',
        sa.Column('chat_enabled', sa.Boolean(), nullable=False, server_default='1'),
    )


def downgrade():
    op.drop_column('user_details', 'chat_enabled')
