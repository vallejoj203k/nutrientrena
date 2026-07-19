"""add movement_pattern to trainings

Patrón de movimiento del formulario 'Información avanzada'
del prototipo de la librería de ejercicios.

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'd9e0f1a2b3c4'
down_revision = 'c8d9e0f1a2b3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('trainings', sa.Column('movement_pattern', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('trainings', 'movement_pattern')
