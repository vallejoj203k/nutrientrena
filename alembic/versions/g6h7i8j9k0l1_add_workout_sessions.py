"""add workout_sessions table

Revision ID: g6h7i8j9k0l1
Revises: f5g6h7i8j9k0
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'g6h7i8j9k0l1'
down_revision = 'f5g6h7i8j9k0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'workout_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_user_detail_id', sa.String(36), nullable=False),
        sa.Column('routine_id', sa.Integer(), nullable=True),
        sa.Column('session_date', sa.Date(), nullable=False),
        sa.Column('duration_min', sa.Integer(), nullable=True),
        sa.Column('rpe', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_user_detail_id'], ['user_details.id']),
        sa.ForeignKeyConstraint(['routine_id'], ['routines.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('workout_sessions')
