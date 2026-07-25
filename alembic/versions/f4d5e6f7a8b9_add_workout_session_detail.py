"""add workout session detail (ejercicios y series por sesión)

Revision ID: f4d5e6f7a8b9
Revises: f3c4d5e6f7a8
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = 'f4d5e6f7a8b9'
down_revision = 'f3c4d5e6f7a8'
branch_labels = None
depends_on = None


def _has_table(name):
    bind = op.get_bind()
    try:
        return name in sa.inspect(bind).get_table_names()
    except Exception:
        return False


def upgrade():
    if not _has_table('workout_session_exercises'):
        op.create_table(
            'workout_session_exercises',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('workout_sessions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('training_id', sa.Integer(), sa.ForeignKey('trainings.id'), nullable=True),
            sa.Column('name', sa.String(255), nullable=True),
            sa.Column('muscle_group_name', sa.String(255), nullable=True),
            sa.Column('order_index', sa.Integer(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_wse_session', 'workout_session_exercises', ['session_id'])
        op.create_index('ix_wse_training', 'workout_session_exercises', ['training_id'])

    if not _has_table('workout_session_sets'):
        op.create_table(
            'workout_session_sets',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('session_exercise_id', sa.Integer(), sa.ForeignKey('workout_session_exercises.id', ondelete='CASCADE'), nullable=False),
            sa.Column('set_number', sa.Integer(), nullable=False),
            sa.Column('reps', sa.String(20), nullable=True),
            sa.Column('weight', sa.Float(), nullable=True),
            sa.Column('rpe', sa.Float(), nullable=True),
            sa.Column('done', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_wss_exercise', 'workout_session_sets', ['session_exercise_id'])


def downgrade():
    if _has_table('workout_session_sets'):
        op.drop_table('workout_session_sets')
    if _has_table('workout_session_exercises'):
        op.drop_table('workout_session_exercises')
