"""advanced routine builder

Revision ID: f5g6h7i8j9k0
Revises: e5f6a7b8c9d0
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'f5g6h7i8j9k0'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    # Add icon column to muscle_groups
    op.add_column('muscle_groups', sa.Column('icon', sa.String(10), nullable=True))

    # Add new columns to trainings
    op.add_column('trainings', sa.Column('exercise_type', sa.String(20), nullable=True))
    op.add_column('trainings', sa.Column('location', sa.String(20), nullable=True))
    op.add_column('trainings', sa.Column('secondary_muscle_group_id', sa.Integer(), sa.ForeignKey('muscle_groups.id'), nullable=True))

    # Create routine_blocks table
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

    # Add new columns to routine_day_details
    op.add_column('routine_day_details', sa.Column('block_id', sa.Integer(), sa.ForeignKey('routine_blocks.id'), nullable=True))
    op.add_column('routine_day_details', sa.Column('intensity_type', sa.String(20), nullable=True))
    op.add_column('routine_day_details', sa.Column('intensity_value', sa.Float(), nullable=True))
    op.add_column('routine_day_details', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('routine_day_details', sa.Column('order_index', sa.Integer(), server_default='0'))


def downgrade():
    op.drop_column('routine_day_details', 'order_index')
    op.drop_column('routine_day_details', 'notes')
    op.drop_column('routine_day_details', 'intensity_value')
    op.drop_column('routine_day_details', 'intensity_type')
    op.drop_column('routine_day_details', 'block_id')

    op.drop_table('routine_blocks')

    op.drop_column('trainings', 'secondary_muscle_group_id')
    op.drop_column('trainings', 'location')
    op.drop_column('trainings', 'exercise_type')

    op.drop_column('muscle_groups', 'icon')
