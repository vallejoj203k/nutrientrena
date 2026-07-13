"""add lifecycle_status to user_details

Adds a client lifecycle status (activo/pendiente/pausado/finalizado),
independent from the CRM status_id, used by the Clientes page tabs.
Existing rows are backfilled to "activo".

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user_details',
        sa.Column('lifecycle_status', sa.String(20), nullable=False, server_default='activo'),
    )
    op.execute("UPDATE user_details SET lifecycle_status = 'activo' WHERE lifecycle_status IS NULL")


def downgrade():
    op.drop_column('user_details', 'lifecycle_status')
