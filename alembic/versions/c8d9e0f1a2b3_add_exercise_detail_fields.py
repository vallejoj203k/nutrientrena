"""add exercise detail fields to trainings

Campos del prototipo de la librería de ejercicios: material,
dificultad y series/reps/descanso recomendados.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'c8d9e0f1a2b3'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('trainings', sa.Column('material', sa.String(120), nullable=True))
    op.add_column('trainings', sa.Column('difficulty', sa.Integer(), nullable=True))
    op.add_column('trainings', sa.Column('rec_series', sa.String(40), nullable=True))
    op.add_column('trainings', sa.Column('rec_reps', sa.String(40), nullable=True))
    op.add_column('trainings', sa.Column('rec_rest', sa.String(40), nullable=True))


def downgrade():
    op.drop_column('trainings', 'rec_rest')
    op.drop_column('trainings', 'rec_reps')
    op.drop_column('trainings', 'rec_series')
    op.drop_column('trainings', 'difficulty')
    op.drop_column('trainings', 'material')
