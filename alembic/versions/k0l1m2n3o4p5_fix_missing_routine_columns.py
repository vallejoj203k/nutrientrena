"""fix missing routine columns

Revision ID: k0l1m2n3o4p5
Revises: j9k0l1m2n3o4
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = 'k0l1m2n3o4p5'
down_revision = 'j9k0l1m2n3o4'
branch_labels = None
depends_on = None


def _col_exists(inspector, table, column):
    return any(c['name'] == column for c in inspector.get_columns(table))


def _table_exists(inspector, table):
    return table in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # ── routines.notes ────────────────────────────────────────────────────────
    if not _col_exists(insp, 'routines', 'notes'):
        op.add_column('routines', sa.Column('notes', sa.Text(), nullable=True))

    # ── muscle_groups.icon ────────────────────────────────────────────────────
    if not _col_exists(insp, 'muscle_groups', 'icon'):
        op.add_column('muscle_groups', sa.Column('icon', sa.String(10), nullable=True))

    # ── trainings new columns ─────────────────────────────────────────────────
    if not _col_exists(insp, 'trainings', 'exercise_type'):
        op.add_column('trainings', sa.Column('exercise_type', sa.String(20), nullable=True))
    if not _col_exists(insp, 'trainings', 'location'):
        op.add_column('trainings', sa.Column('location', sa.String(20), nullable=True))
    if not _col_exists(insp, 'trainings', 'secondary_muscle_group_id'):
        op.add_column('trainings', sa.Column('secondary_muscle_group_id', sa.Integer(), nullable=True))

    # ── routine_blocks table ──────────────────────────────────────────────────
    if not _table_exists(insp, 'routine_blocks'):
        op.create_table(
            'routine_blocks',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('routine_id', sa.Integer(), sa.ForeignKey('routines.id'), nullable=False),
            sa.Column('routine_day_id', sa.Integer(), sa.ForeignKey('routine_days.id'), nullable=False),
            sa.Column('block_type', sa.String(20), server_default='normal'),
            sa.Column('order_index', sa.Integer(), server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    # ── routine_day_details new columns ───────────────────────────────────────
    if not _col_exists(insp, 'routine_day_details', 'block_id'):
        op.add_column('routine_day_details', sa.Column('block_id', sa.Integer(), nullable=True))
    if not _col_exists(insp, 'routine_day_details', 'intensity_type'):
        op.add_column('routine_day_details', sa.Column('intensity_type', sa.String(20), nullable=True))
    if not _col_exists(insp, 'routine_day_details', 'intensity_value'):
        op.add_column('routine_day_details', sa.Column('intensity_value', sa.Float(), nullable=True))
    if not _col_exists(insp, 'routine_day_details', 'notes'):
        op.add_column('routine_day_details', sa.Column('notes', sa.Text(), nullable=True))
    if not _col_exists(insp, 'routine_day_details', 'order_index'):
        op.add_column('routine_day_details', sa.Column('order_index', sa.Integer(), server_default='0'))


def downgrade():
    op.drop_column('routines', 'notes')
