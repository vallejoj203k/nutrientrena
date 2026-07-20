"""add objective and materials to routines

Campos del formulario 'Información' de nueva rutina del prototipo:
objetivo principal y materiales (multi-selección, CSV).

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

revision = 'e0f1a2b3c4d5'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('routines', sa.Column('objective', sa.String(100), nullable=True))
    op.add_column('routines', sa.Column('materials', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('routines', 'materials')
    op.drop_column('routines', 'objective')
