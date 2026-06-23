"""Allow free-text country names in user_details.country_code

Revision ID: v0w1x2y3z4a5
Revises: u9v0w1x2y3z4
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = 'v0w1x2y3z4a5'
down_revision = 'u9v0w1x2y3z4'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Find the FK constraint name dynamically (MySQL auto-names them)
    result = conn.execute(sa.text("""
        SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'user_details'
          AND COLUMN_NAME = 'country_code'
          AND REFERENCED_TABLE_NAME IS NOT NULL
        LIMIT 1
    """))
    row = result.fetchone()
    if row:
        conn.execute(sa.text(f"ALTER TABLE user_details DROP FOREIGN KEY `{row[0]}`"))

    op.alter_column(
        'user_details', 'country_code',
        existing_type=sa.String(10),
        type_=sa.String(100),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        'user_details', 'country_code',
        existing_type=sa.String(100),
        type_=sa.String(10),
        nullable=True,
    )
