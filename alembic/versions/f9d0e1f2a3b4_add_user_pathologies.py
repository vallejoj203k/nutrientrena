"""add user_pathologies

Las patologías del cliente (celiaquía, intolerancia a la lactosa, diabetes…)
solo podían asociarse a una dieta, no a la persona. Sin ellas ni el coach las
tiene a la vista al planificar ni el generador puede excluir alimentos.

Revision ID: f9d0e1f2a3b4
Revises: f8c9d0e1f2a3
Create Date: 2026-07-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'f9d0e1f2a3b4'
down_revision = 'f8c9d0e1f2a3'
branch_labels = None
depends_on = None


def _has_table(table):
    bind = op.get_bind()
    try:
        return table in sa.inspect(bind).get_table_names()
    except Exception:
        return False


def upgrade():
    if _has_table('user_pathologies'):
        return
    op.create_table(
        'user_pathologies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_detail_id', sa.String(36), nullable=False),
        sa.Column('pathology_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_detail_id'], ['user_details.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pathology_id'], ['pathologies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    if _has_table('user_pathologies'):
        op.drop_table('user_pathologies')
