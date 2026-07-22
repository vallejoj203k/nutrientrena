"""add last_read_at to chat_participants (badge de no leídos)

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'f2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        return column in [c['name'] for c in insp.get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('chat_participants', 'last_read_at'):
        op.add_column('chat_participants', sa.Column('last_read_at', sa.DateTime(), nullable=True))


def downgrade():
    if _has_column('chat_participants', 'last_read_at'):
        op.drop_column('chat_participants', 'last_read_at')
