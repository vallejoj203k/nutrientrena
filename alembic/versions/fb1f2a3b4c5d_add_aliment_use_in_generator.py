"""add use_in_generator a aliments

El catálogo del USDA son 7.348 entradas de referencia nutricional con nombres
de laboratorio ("Abiyuch, sin procesar", "Abadejo de Alaska, crudo"). Sirven
para consultar macros exactos, pero no para construir una dieta que se le
entrega a una persona.

No se borran —están referenciados desde dietas y recetas, y son la referencia
de macros— sino que se marca cuáles puede usar el generador. Por defecto
ninguno: la migración siguiente da de alta un catálogo base y lo marca.

Revision ID: fb1f2a3b4c5d
Revises: fa0e1f2a3b4c
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'fb1f2a3b4c5d'
down_revision = 'fa0e1f2a3b4c'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('aliments', 'use_in_generator'):
        op.add_column(
            'aliments',
            sa.Column('use_in_generator', sa.Boolean(), nullable=False,
                      server_default=sa.false()),
        )


def downgrade():
    if _has_column('aliments', 'use_in_generator'):
        op.drop_column('aliments', 'use_in_generator')
