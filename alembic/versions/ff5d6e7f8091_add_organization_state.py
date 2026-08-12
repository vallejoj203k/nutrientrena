"""add state y country a organizations

El panel de plataforma necesita distinguir el estado de cada cuenta —Activa,
En prueba, Impago, Suspendida— para poder filtrarlas y para que el botón de
suspender signifique algo. Hasta ahora solo había is_active (sí/no), que no
distingue "en prueba" de "activa" ni "impago" de "suspendida a mano".

is_active se conserva y se mantiene en sincronía: hay código que lo consulta y
cambiarlo de golpe sería arriesgar el panel de coach por una mejora del de
admin.

country es informativo, para la columna del listado.

NO se añade nada de planes ni de importes: eso depende de la pasarela de pago,
que está expresamente fuera de alcance por ahora. Poner los campos "por si
acaso" invitaría a rellenarlos a mano y a que luego no cuadren con Stripe.

Revision ID: ff5d6e7f8091
Revises: fe4c5d6e7f80
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa

revision = 'ff5d6e7f8091'
down_revision = 'fe4c5d6e7f80'
branch_labels = None
depends_on = None

ESTADOS = ('activa', 'prueba', 'impago', 'suspendida')


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('organizations', 'state'):
        op.add_column('organizations', sa.Column(
            'state', sa.String(20), nullable=False, server_default='activa'))
        op.create_index('ix_organizations_state', 'organizations', ['state'])
        # Las que ya estaban inactivas pasan a suspendidas, que es lo que
        # significaba is_active=0 en la práctica.
        op.execute("UPDATE organizations SET state='suspendida' WHERE is_active = 0")

    if not _has_column('organizations', 'country'):
        op.add_column('organizations', sa.Column('country', sa.String(100), nullable=True))


def downgrade():
    if _has_column('organizations', 'country'):
        op.drop_column('organizations', 'country')
    if _has_column('organizations', 'state'):
        op.drop_index('ix_organizations_state', table_name='organizations')
        op.drop_column('organizations', 'state')
