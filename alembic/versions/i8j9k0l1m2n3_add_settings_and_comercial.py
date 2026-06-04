"""add app_settings and fecha_renovacion

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'i8j9k0l1m2n3'
down_revision = 'h7i8j9k0l1m2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_name', sa.String(255), nullable=True),
        sa.Column('business_email', sa.String(255), nullable=True),
        sa.Column('business_phone', sa.String(50), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True, server_default='EUR'),
        sa.Column('renewal_alert_days', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('timezone', sa.String(50), nullable=True, server_default='Europe/Madrid'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('user_details', sa.Column('fecha_renovacion', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('user_details', 'fecha_renovacion')
    op.drop_table('app_settings')
