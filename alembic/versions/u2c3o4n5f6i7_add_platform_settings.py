"""Ajustes de plataforma y fin de prueba de cada cuenta

Dos cosas que la sección "Configuración" del panel necesita y no existían:

- platform_settings: los ajustes de Alzum (nombre, correo de soporte, moneda
  por defecto, días de prueba, registro abierto y modo mantenimiento). Tabla
  aparte de app_settings a propósito: aquella guarda los datos del NEGOCIO DEL
  COACH y la edita él desde su panel. Mezclarlas habría juntado dos niveles de
  la jerarquía en la misma fila.
- organizations.trial_ends_at: sin esto, "días de prueba gratuita" sería un
  número guardado que no le pasa a nadie. Al dar de alta una cuenta en prueba
  se calcula y se guarda su fecha de fin, y la ficha la enseña.

Revision ID: u2c3o4n5f6i7
Revises: t1e2a3m4a5l6
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'u2c3o4n5f6i7'
down_revision = 't1e2a3m4a5l6'
branch_labels = None
depends_on = None


def _tiene_tabla(nombre):
    return sa.inspect(op.get_bind()).has_table(nombre)


def _tiene_columna(tabla, columna):
    try:
        return columna in [c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabla)]
    except Exception:
        return False


def upgrade():
    if not _tiene_tabla('platform_settings'):
        op.create_table(
            'platform_settings',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('platform_name', sa.String(120), nullable=False, server_default='Alzum.io'),
            sa.Column('support_email', sa.String(255), nullable=True),
            sa.Column('default_currency', sa.String(10), nullable=False, server_default='EUR'),
            sa.Column('trial_days', sa.Integer, nullable=False, server_default='14'),
            sa.Column('open_registration', sa.Boolean, nullable=False, server_default='0'),
            sa.Column('maintenance_mode', sa.Boolean, nullable=False, server_default='0'),
            sa.Column('updated_at', sa.DateTime, nullable=True),
        )

    if not _tiene_columna('organizations', 'trial_ends_at'):
        op.add_column('organizations', sa.Column('trial_ends_at', sa.DateTime(), nullable=True))


def downgrade():
    if _tiene_columna('organizations', 'trial_ends_at'):
        op.drop_column('organizations', 'trial_ends_at')
    if _tiene_tabla('platform_settings'):
        op.drop_table('platform_settings')
