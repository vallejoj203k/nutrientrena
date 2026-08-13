"""Notas internas de cada cuenta

La ficha de un coach en el panel de plataforma lleva un campo de notas del
equipo de Alzum: para acordarse de por qué se le hizo un precio especial, o de
que la última incidencia venía de ahí.

Son INTERNAS: el coach no las ve por ninguna vía. Va aquí y no en un comentario
suelto porque una nota que vive en la cabeza de quien la escribió se pierde en
cuanto atiende la cuenta otra persona.

Revision ID: w4n5o6t7a8s9
Revises: v3p4l5a6n7e8
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'w4n5o6t7a8s9'
down_revision = 'v3p4l5a6n7e8'
branch_labels = None
depends_on = None


def _tiene_columna(tabla, columna):
    try:
        return columna in [c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabla)]
    except Exception:
        return False


def upgrade():
    if not _tiene_columna('organizations', 'internal_notes'):
        op.add_column('organizations', sa.Column('internal_notes', sa.Text(), nullable=True))


def downgrade():
    if _tiene_columna('organizations', 'internal_notes'):
        op.drop_column('organizations', 'internal_notes')
