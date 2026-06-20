"""add calendar_tasks table

Revision ID: t8u9v0w1x2y3
Revises: s7t8u9v0w1x2
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

revision = 't8u9v0w1x2y3'
down_revision = 's7t8u9v0w1x2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'calendar_tasks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('client_user_detail_id', sa.String(36),
                  sa.ForeignKey('user_details.id'), nullable=False),
        sa.Column('coach_user_id', sa.Integer,
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('task_date', sa.Date, nullable=False),
        sa.Column('task_type', sa.String(30), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('done', sa.Boolean, default=False, nullable=False),
        sa.Column('done_at', sa.DateTime, nullable=True),
        sa.Column('recurrence', sa.String(20), default='none', nullable=True),
        sa.Column('recurrence_end_date', sa.Date, nullable=True),
        sa.Column('recurrence_group_id', sa.Integer, nullable=True),
        sa.Column('checkin_id', sa.String(36),
                  sa.ForeignKey('weekly_checkins.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )

    op.create_index('ix_calendar_tasks_client_date',
                    'calendar_tasks',
                    ['client_user_detail_id', 'task_date'])
    op.create_index('ix_calendar_tasks_recurrence_group',
                    'calendar_tasks',
                    ['recurrence_group_id'])


def downgrade() -> None:
    op.drop_index('ix_calendar_tasks_recurrence_group', table_name='calendar_tasks')
    op.drop_index('ix_calendar_tasks_client_date', table_name='calendar_tasks')
    op.drop_table('calendar_tasks')
