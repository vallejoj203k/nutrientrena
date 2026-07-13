"""add documents table

Almacén de documentos (PDFs) que el coach sube a la Librería, agrupados
por categoría (contratos/guias/plantillas).

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('client_user_detail_id', sa.String(36), sa.ForeignKey('user_details.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(30), nullable=False, server_default='guias'),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_key', sa.String(500), nullable=True),
        sa.Column('size_kb', sa.Float(), nullable=True),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_documents_coach_category', 'documents', ['coach_id', 'category'])


def downgrade():
    op.drop_index('ix_documents_coach_category', table_name='documents')
    op.drop_table('documents')
