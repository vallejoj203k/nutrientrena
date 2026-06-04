"""add progress photos and event recurrence

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'j9k0l1m2n3o4'
down_revision = 'i8j9k0l1m2n3'
branch_labels = None
depends_on = None


def upgrade():
    # ── Progress: 2 additional photo slots ───────────────────────────────────
    op.add_column('progress_day_users', sa.Column('photo2', sa.String(500), nullable=True))
    op.add_column('progress_day_users', sa.Column('photo3', sa.String(500), nullable=True))

    # ── Events: recurrence support ────────────────────────────────────────────
    op.add_column('event_users', sa.Column('recurrence', sa.String(20), nullable=True))
    op.add_column('event_users', sa.Column('recurrence_end_date', sa.Date(), nullable=True))
    op.add_column('event_users', sa.Column('recurrence_group_id', sa.Integer(), nullable=True))
    op.create_index('ix_event_users_group', 'event_users', ['recurrence_group_id'])


def downgrade():
    op.drop_index('ix_event_users_group', table_name='event_users')
    op.drop_column('event_users', 'recurrence_group_id')
    op.drop_column('event_users', 'recurrence_end_date')
    op.drop_column('event_users', 'recurrence')
    op.drop_column('progress_day_users', 'photo3')
    op.drop_column('progress_day_users', 'photo2')
