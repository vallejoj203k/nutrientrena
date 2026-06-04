"""add client_tasks table

Revision ID: h7i8j9k0l1m2
Revises: g6h7i8j9k0l1
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'h7i8j9k0l1m2'
down_revision = 'g6h7i8j9k0l1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'client_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_user_detail_id', sa.String(36), nullable=False),
        sa.Column('task_type', sa.String(20), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('done', sa.Boolean(), default=False),
        sa.Column('week_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_user_detail_id'], ['user_details.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_client_tasks_week', 'client_tasks', ['week_date'])
    op.create_index('ix_client_tasks_client', 'client_tasks', ['client_user_detail_id'])


def downgrade():
    op.drop_table('client_tasks')
