"""add weekly_menus and weekly_menu_days tables

Revision ID: o3p4q5r6s7t8
Revises: n2o3p4q5r6s7
Create Date: 2026-06-17

"""
from alembic import op
import sqlalchemy as sa

revision = 'o3p4q5r6s7t8'
down_revision = 'n2o3p4q5r6s7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'weekly_menus',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('coach_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['coach_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_weekly_menus_coach_id', 'weekly_menus', ['coach_id'])

    op.create_table(
        'weekly_menu_days',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('menu_id', sa.String(36), nullable=False),
        sa.Column('day_index', sa.Integer(), nullable=False),
        sa.Column('diet_id', sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(['menu_id'], ['weekly_menus.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['diet_id'], ['diets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_weekly_menu_days_menu_id', 'weekly_menu_days', ['menu_id'])


def downgrade() -> None:
    op.drop_table('weekly_menu_days')
    op.drop_table('weekly_menus')
