"""add client aliments

Revision ID: r6s7t8u9v0w1
Revises: q5r6s7t8u9v0
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

revision = 'r6s7t8u9v0w1'
down_revision = 'q5r6s7t8u9v0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'client_aliments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('client_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('group_food_id', sa.Integer, sa.ForeignKey('group_foods.id'), nullable=True),
        sa.Column('brand', sa.String(255), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('quantity', sa.Float, nullable=True),
        sa.Column('proteins', sa.Float, nullable=True),
        sa.Column('carbohydrates', sa.Float, nullable=True),
        sa.Column('fats', sa.Float, nullable=True),
        sa.Column('calories', sa.Float, nullable=True),
        sa.Column('comments', sa.Text, nullable=True),
        sa.Column('created_user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('client_aliments')
