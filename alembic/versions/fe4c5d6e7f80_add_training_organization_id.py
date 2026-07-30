"""add organization_id y created_user_id a trainings

El catálogo de ejercicios era completamente plano: todo `Training` era global
y cualquier coach podía editar o borrar el ejercicio de cualquier otro, de
cualquier organización. El DELETE además desengancha las referencias en
`routine_day_details`, así que borrar un ejercicio ajeno rompía las rutinas de
otra organización sin avisar.

Se añaden las dos columnas que ya tienen alimentos, rutinas y dietas:
- organization_id: NULL = catálogo maestro de plataforma (todo lo existente
  se queda así, que es lo correcto: la base compartida sigue compartida).
- created_user_id: quién lo creó, para que su autor siempre pueda editar lo
  suyo aunque no tenga organización (misma regla que en rutinas).

Revision ID: fe4c5d6e7f80
Revises: fd3b4c5d6e7f
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = 'fe4c5d6e7f80'
down_revision = 'fd3b4c5d6e7f'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    try:
        return column in [c['name'] for c in sa.inspect(bind).get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('trainings', 'organization_id'):
        op.add_column('trainings', sa.Column('organization_id', sa.String(36), nullable=True))
        op.create_foreign_key(
            'fk_trainings_organization_id',
            'trainings', 'organizations',
            ['organization_id'], ['id'],
            ondelete='SET NULL',
        )
        op.create_index('ix_trainings_organization_id', 'trainings', ['organization_id'])

    if not _has_column('trainings', 'created_user_id'):
        op.add_column('trainings', sa.Column('created_user_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_trainings_created_user_id',
            'trainings', 'users',
            ['created_user_id'], ['id'],
            ondelete='SET NULL',
        )


def downgrade():
    if _has_column('trainings', 'created_user_id'):
        op.drop_constraint('fk_trainings_created_user_id', 'trainings', type_='foreignkey')
        op.drop_column('trainings', 'created_user_id')

    if _has_column('trainings', 'organization_id'):
        op.drop_index('ix_trainings_organization_id', table_name='trainings')
        op.drop_constraint('fk_trainings_organization_id', 'trainings', type_='foreignkey')
        op.drop_column('trainings', 'organization_id')
