"""add category to form_templates

Adds a `category` column to form_templates so the Librería › Formularios
view can group templates into Check-ins, Onboarding and Encuestas.
Existing rows are backfilled to "checkin".

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa

revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'form_templates',
        sa.Column('category', sa.String(30), nullable=False, server_default='checkin'),
    )
    # Backfill existing rows explicitly (server_default already covers new rows).
    op.execute("UPDATE form_templates SET category = 'checkin' WHERE category IS NULL")


def downgrade():
    op.drop_column('form_templates', 'category')
