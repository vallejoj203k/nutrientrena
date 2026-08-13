"""Catálogo de planes de la plataforma

Lo que Alzum le vende a un coach: nombre, precios, límites y funcionalidades.
Es el CATÁLOGO, no la facturación —definir cuánto cuesta el plan Pro no
necesita pasarela de pago; cobrarlo sí, y eso sigue fuera de alcance—.

La tabla se llama platform_plans y el modelo SubscriptionPlan para no chocar
con PlanDelivery, que es otra cosa completamente distinta (el envío de un plan
de dieta y rutina a un cliente).

organizations.plan_id: sin esto, el "N cuenta(s)" de cada tarjeta sería
siempre cero, y una pantalla que existe para decidir precios estaría llena de
números muertos.

Revision ID: v3p4l5a6n7e8
Revises: u2c3o4n5f6i7
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'v3p4l5a6n7e8'
down_revision = 'u2c3o4n5f6i7'
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
    if not _tiene_tabla('platform_plans'):
        op.create_table(
            'platform_plans',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(80), nullable=False),
            sa.Column('price_month', sa.Float, nullable=False, server_default='0'),
            sa.Column('price_year_month', sa.Float, nullable=True),
            sa.Column('default_cycle', sa.String(10), nullable=False, server_default='mensual'),
            sa.Column('max_clients', sa.Integer, nullable=False, server_default='0'),
            sa.Column('coaches_included', sa.Integer, nullable=False, server_default='1'),
            sa.Column('extra_coach_price', sa.Float, nullable=True),
            sa.Column('storage', sa.String(60), nullable=True),
            sa.Column('support', sa.String(120), nullable=True),
            sa.Column('features', sa.Text, nullable=True),
            sa.Column('visible', sa.Boolean, nullable=False, server_default='1'),
            sa.Column('highlighted', sa.Boolean, nullable=False, server_default='0'),
            sa.Column('order_index', sa.Integer, nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime, nullable=True),
            sa.Column('updated_at', sa.DateTime, nullable=True),
        )

    if not _tiene_columna('organizations', 'plan_id'):
        op.add_column('organizations', sa.Column('plan_id', sa.Integer, nullable=True))
        op.create_foreign_key('fk_organizations_plan', 'organizations',
                              'platform_plans', ['plan_id'], ['id'])


def downgrade():
    if _tiene_columna('organizations', 'plan_id'):
        try:
            op.drop_constraint('fk_organizations_plan', 'organizations', type_='foreignkey')
        except Exception:
            pass
        op.drop_column('organizations', 'plan_id')
    if _tiene_tabla('platform_plans'):
        op.drop_table('platform_plans')
