"""add name to weekly_menu_days

Permite que el coach renombre los días del menú ("Lunes", "Día de
entreno"…) en el constructor de menús. Null = "Día N" por defecto.

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'a6b7c8d9e0f1'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('weekly_menu_days', sa.Column('name', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('weekly_menu_days', 'name')
