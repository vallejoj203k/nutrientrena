"""add measurements to weekly_checkins

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('weekly_checkins', sa.Column('photo_url', sa.String(500), nullable=True))
    op.add_column('weekly_checkins', sa.Column('body_fat',  sa.Float(),      nullable=True))
    op.add_column('weekly_checkins', sa.Column('waist',     sa.Float(),      nullable=True))
    op.add_column('weekly_checkins', sa.Column('chest',     sa.Float(),      nullable=True))
    op.add_column('weekly_checkins', sa.Column('hips',      sa.Float(),      nullable=True))
    op.add_column('weekly_checkins', sa.Column('arms',      sa.Float(),      nullable=True))
    op.add_column('weekly_checkins', sa.Column('legs',      sa.Float(),      nullable=True))


def downgrade():
    for col in ('photo_url', 'body_fat', 'waist', 'chest', 'hips', 'arms', 'legs'):
        op.drop_column('weekly_checkins', col)
