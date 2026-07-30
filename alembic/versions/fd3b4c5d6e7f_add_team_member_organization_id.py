"""add organization_id a team_members

TeamMember (la tabla real detrás de la pantalla "Coaches"/Equipo) no tenía
ninguna relación con Organization: era una tabla plana de toda la plataforma,
visible y editable por cualquier ADMIN sin importar de qué organización fuera
cada miembro. Con la Fase 2 (un ADMIN dueño de organización ya actúa dentro de
ella) ese hueco se vuelve real: dos organizaciones distintas verían y podrían
tocar el equipo la una de la otra.

Revision ID: fd3b4c5d6e7f
Revises: fc2a3b4c5d6e
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = 'fd3b4c5d6e7f'
down_revision = 'fc2a3b4c5d6e'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('team_members', 'organization_id'):
        op.add_column('team_members', sa.Column('organization_id', sa.String(36), nullable=True))
        op.create_foreign_key(
            'fk_team_members_organization_id',
            'team_members', 'organizations',
            ['organization_id'], ['id'],
            ondelete='SET NULL',
        )
        op.create_index('ix_team_members_organization_id', 'team_members', ['organization_id'])


def downgrade():
    if _has_column('team_members', 'organization_id'):
        op.drop_index('ix_team_members_organization_id', table_name='team_members')
        op.drop_constraint('fk_team_members_organization_id', 'team_members', type_='foreignkey')
        op.drop_column('team_members', 'organization_id')
