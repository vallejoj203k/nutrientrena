"""add contracts and contract templates

Revision ID: bc1de2ef3fa4
Revises: ab2bc3cd4de5
Create Date: 2026-06-25
"""
from alembic import op
from sqlalchemy import text

revision = 'bc1de2ef3fa4'
down_revision = 'ab2bc3cd4de5'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS contract_templates (
            id         INT NOT NULL AUTO_INCREMENT,
            coach_id   INT NOT NULL,
            title      VARCHAR(255) NOT NULL,
            type       VARCHAR(50) NOT NULL DEFAULT 'servicio',
            content    TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT fk_ct_coach FOREIGN KEY (coach_id) REFERENCES users(id)
        ) DEFAULT CHARSET=utf8mb4
    """))

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS contracts (
            id          INT NOT NULL AUTO_INCREMENT,
            coach_id    INT NOT NULL,
            client_id   VARCHAR(36),
            template_id INT,
            title       VARCHAR(255) NOT NULL,
            type        VARCHAR(50) NOT NULL DEFAULT 'servicio',
            content     TEXT NOT NULL,
            status      VARCHAR(20) NOT NULL DEFAULT 'borrador',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT fk_c_coach    FOREIGN KEY (coach_id)    REFERENCES users(id),
            CONSTRAINT fk_c_client   FOREIGN KEY (client_id)   REFERENCES user_details(id) ON DELETE SET NULL,
            CONSTRAINT fk_c_template FOREIGN KEY (template_id) REFERENCES contract_templates(id) ON DELETE SET NULL
        ) DEFAULT CHARSET=utf8mb4
    """))


def downgrade():
    bind = op.get_bind()
    bind.execute(text("DROP TABLE IF EXISTS contracts"))
    bind.execute(text("DROP TABLE IF EXISTS contract_templates"))
