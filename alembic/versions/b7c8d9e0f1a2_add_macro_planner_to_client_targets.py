"""add macro planner fields to client_targets

Persistencia del planificador de macros del perfil del cliente:
ratios de proteína/grasa en g por kg de masa magra y nº de comidas.

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7c8d9e0f1a2'
down_revision = 'a6b7c8d9e0f1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('client_targets', sa.Column('protein_ratio', sa.Float(), nullable=True))
    op.add_column('client_targets', sa.Column('fat_ratio', sa.Float(), nullable=True))
    op.add_column('client_targets', sa.Column('meal_count', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('client_targets', 'meal_count')
    op.drop_column('client_targets', 'fat_ratio')
    op.drop_column('client_targets', 'protein_ratio')
