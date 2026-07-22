"""add client_menus (asignación de menú semanal a cliente)

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'e0f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'client_menus',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('client_user_detail_id', sa.String(36), sa.ForeignKey('user_details.id'), nullable=False),
        sa.Column('menu_id', sa.String(36), sa.ForeignKey('weekly_menus.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_client_menus_client', 'client_menus', ['client_user_detail_id'])


def downgrade():
    op.drop_index('ix_client_menus_client', table_name='client_menus')
    op.drop_table('client_menus')
