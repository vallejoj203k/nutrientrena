"""add_business_fields_to_user_details

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_details', sa.Column('plan_comprado', sa.String(255), nullable=True))
    op.add_column('user_details', sa.Column('precio', sa.Float, nullable=True))
    op.add_column('user_details', sa.Column('estado_pago', sa.String(50), nullable=True))
    op.add_column('user_details', sa.Column('importe_pagado', sa.Float, nullable=True))
    op.add_column('user_details', sa.Column('importe_pendiente', sa.Float, nullable=True))
    op.add_column('user_details', sa.Column('metodo_pago', sa.String(100), nullable=True))
    op.add_column('user_details', sa.Column('fecha_compra', sa.Date, nullable=True))
    op.add_column('user_details', sa.Column('fecha_limite_entrega', sa.Date, nullable=True))
    op.add_column('user_details', sa.Column('responsable_venta', sa.String(255), nullable=True))
    op.add_column('user_details', sa.Column('crm_origen', sa.String(255), nullable=True))
    op.add_column('user_details', sa.Column('whatsapp_link', sa.String(500), nullable=True))
    op.add_column('user_details', sa.Column('consentimiento_evolucion', sa.Boolean, nullable=True, server_default=sa.false()))


def downgrade():
    op.drop_column('user_details', 'consentimiento_evolucion')
    op.drop_column('user_details', 'whatsapp_link')
    op.drop_column('user_details', 'crm_origen')
    op.drop_column('user_details', 'responsable_venta')
    op.drop_column('user_details', 'fecha_limite_entrega')
    op.drop_column('user_details', 'fecha_compra')
    op.drop_column('user_details', 'metodo_pago')
    op.drop_column('user_details', 'importe_pendiente')
    op.drop_column('user_details', 'importe_pagado')
    op.drop_column('user_details', 'estado_pago')
    op.drop_column('user_details', 'precio')
    op.drop_column('user_details', 'plan_comprado')
