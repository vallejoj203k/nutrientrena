"""add contracts and contract templates

Revision ID: bc1de2ef3fa4
Revises: ab2bc3cd4de5
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'bc1de2ef3fa4'
down_revision = 'ab2bc3cd4de5'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    bind = op.get_bind()
    existing = inspect(bind).get_table_names()

    if 'contract_templates' not in existing:
        op.create_table(
            'contract_templates',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('type', sa.String(50), nullable=False, server_default='servicio'),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    if 'contracts' not in existing:
        op.create_table(
            'contracts',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('client_id', sa.Integer(), sa.ForeignKey('user_details.id'), nullable=True),
            sa.Column('template_id', sa.Integer(), sa.ForeignKey('contract_templates.id', ondelete='SET NULL'), nullable=True),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('type', sa.String(50), nullable=False, server_default='servicio'),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='borrador'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )


def downgrade():
    op.drop_table('contracts')
    op.drop_table('contract_templates')
