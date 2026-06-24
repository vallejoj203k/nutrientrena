"""Add organizations, organization_members, and organization_id to content tables

Revision ID: aa1bb2cc3dd4
Revises: z3a4b5c6d7e8
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'aa1bb2cc3dd4'
down_revision = 'z3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. organizations table ─────────────────────────────────────────────
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=True),
        sa.Column('owner_id', sa.String(36), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['user_details.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_organizations_owner_id', 'organizations', ['owner_id'])

    # ── 2. organization_members table ──────────────────────────────────────
    op.create_table(
        'organization_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('user_detail_id', sa.String(36), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_detail_id'], ['user_details.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_org_members_org_id', 'organization_members', ['organization_id'])
    op.create_index('ix_org_members_user_detail_id', 'organization_members', ['user_detail_id'])

    # ── 3. Add organization_id to content tables ───────────────────────────
    for table in ('aliments', 'recipes', 'routines', 'diets', 'weekly_menus'):
        op.add_column(table, sa.Column('organization_id', sa.String(36), nullable=True))
        op.create_foreign_key(
            f'fk_{table}_organization_id',
            table, 'organizations',
            ['organization_id'], ['id'],
            ondelete='SET NULL',
        )
        op.create_index(f'ix_{table}_organization_id', table, ['organization_id'])

    # ── 4. Data migration: create one org per existing coach/admin ─────────
    conn = op.get_bind()

    coaches = conn.execute(text("""
        SELECT DISTINCT ud.id, ud.name, u.id as user_id
        FROM user_details ud
        JOIN users u ON u.id = ud.user_id
        JOIN role_user ru ON ru.user_id = u.id
        WHERE ru.role_id IN (2, 5)
    """)).fetchall()

    import uuid
    from datetime import datetime

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    for coach in coaches:
        org_id = str(uuid.uuid4())
        base_slug = (coach.name or 'org').lower().replace(' ', '-')[:50]
        slug = f"{base_slug}-{org_id[:8]}"

        conn.execute(text("""
            INSERT INTO organizations (id, name, slug, owner_id, is_active, created_at, updated_at)
            VALUES (:id, :name, :slug, :owner_id, 1, :now, :now)
        """), {
            'id': org_id,
            'name': coach.name or 'Mi organización',
            'slug': slug,
            'owner_id': coach.id,
            'now': now,
        })


def downgrade() -> None:
    for table in ('aliments', 'recipes', 'routines', 'diets', 'weekly_menus'):
        op.drop_constraint(f'fk_{table}_organization_id', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_organization_id', table_name=table)
        op.drop_column(table, 'organization_id')

    op.drop_table('organization_members')
    op.drop_table('organizations')
