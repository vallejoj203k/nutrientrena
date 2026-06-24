"""Make user_detail_id nullable, add member_name and member_email to team_members

Revision ID: z3a4b5c6d7e8
Revises: y2z3a4b5c6d7
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'z3a4b5c6d7e8'
down_revision = 'y2z3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    # Drop FK and unique constraint first, then alter column to nullable
    op.drop_constraint('team_members_ibfk_1', 'team_members', type_='foreignkey')
    op.drop_constraint('user_detail_id', 'team_members', type_='unique')

    op.alter_column('team_members', 'user_detail_id',
                    existing_type=sa.String(36),
                    nullable=True)

    # Re-create FK (nullable now)
    op.create_foreign_key(
        'team_members_ibfk_1', 'team_members', 'user_details',
        ['user_detail_id'], ['id']
    )

    op.add_column('team_members', sa.Column('member_name', sa.String(200), nullable=True))
    op.add_column('team_members', sa.Column('member_email', sa.String(200), nullable=True))


def downgrade():
    op.drop_column('team_members', 'member_email')
    op.drop_column('team_members', 'member_name')
    op.drop_constraint('team_members_ibfk_1', 'team_members', type_='foreignkey')
    op.alter_column('team_members', 'user_detail_id',
                    existing_type=sa.String(36),
                    nullable=False)
    op.create_unique_constraint('user_detail_id', 'team_members', ['user_detail_id'])
    op.create_foreign_key(
        'team_members_ibfk_1', 'team_members', 'user_details',
        ['user_detail_id'], ['id']
    )
