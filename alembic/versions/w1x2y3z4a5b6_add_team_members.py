"""Add team_members table

Revision ID: w1x2y3z4a5b6
Revises: v0w1x2y3z4a5
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'w1x2y3z4a5b6'
down_revision = 'v0w1x2y3z4a5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_detail_id', sa.String(36), nullable=False),
        sa.Column('role_label', sa.String(100), nullable=True),
        sa.Column('hours_week', sa.Integer(), nullable=True),
        sa.Column('salary_fijo', sa.Float(), nullable=True),
        sa.Column('commission', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_detail_id'], ['user_details.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_detail_id'),
    )


def downgrade():
    op.drop_table('team_members')
