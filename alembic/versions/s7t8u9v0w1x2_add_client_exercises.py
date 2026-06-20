"""add client exercises

Revision ID: s7t8u9v0w1x2
Revises: r6s7t8u9v0w1
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

revision = 's7t8u9v0w1x2'
down_revision = 'r6s7t8u9v0w1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'client_exercises',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('client_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('muscle_group_id', sa.Integer, sa.ForeignKey('muscle_groups.id'), nullable=True),
        sa.Column('secondary_muscle_group_id', sa.Integer, sa.ForeignKey('muscle_groups.id'), nullable=True),
        sa.Column('image', sa.String(500), nullable=True),
        sa.Column('video_url', sa.String(500), nullable=True),
        sa.Column('exercise_type', sa.String(20), nullable=True),
        sa.Column('location', sa.String(20), nullable=True),
        sa.Column('created_user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('client_exercises')
