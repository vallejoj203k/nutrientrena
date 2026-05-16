"""add weekly checkins

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'weekly_checkins',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('client_user_detail_id', sa.String(36), sa.ForeignKey('user_details.id'), nullable=False),
        sa.Column('coach_user_detail_id',  sa.String(36), sa.ForeignKey('user_details.id'), nullable=True),
        sa.Column('checkin_date', sa.Date(), nullable=False),
        sa.Column('weight',       sa.Float(), nullable=True),
        sa.Column('notes',        sa.Text(), nullable=True),
        sa.Column('coach_notes',  sa.Text(), nullable=True),
        sa.Column('created_at',   sa.DateTime(), nullable=True),
        sa.Column('updated_at',   sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('weekly_checkins')
