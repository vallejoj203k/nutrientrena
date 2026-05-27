"""add_plan_deliveries_table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'plan_deliveries',
        sa.Column('id',                      sa.String(36),  primary_key=True),
        sa.Column('client_user_detail_id',   sa.String(36),  sa.ForeignKey('user_details.id'), nullable=False),
        sa.Column('coach_user_detail_id',    sa.String(36),  sa.ForeignKey('user_details.id'), nullable=True),
        sa.Column('diet_id',                 sa.String(36),  sa.ForeignKey('diets.id'),        nullable=True),
        sa.Column('routine_id',              sa.Integer(),   sa.ForeignKey('routines.id'),     nullable=True),
        sa.Column('message',                 sa.Text(),      nullable=True),
        sa.Column('loom_link',               sa.String(500), nullable=True),
        sa.Column('email_sent',              sa.Boolean(),   nullable=False, server_default=sa.false()),
        sa.Column('delivered_at',            sa.DateTime(),  nullable=False),
    )
    op.create_index('ix_plan_deliveries_client', 'plan_deliveries', ['client_user_detail_id'])


def downgrade():
    op.drop_index('ix_plan_deliveries_client', table_name='plan_deliveries')
    op.drop_table('plan_deliveries')
