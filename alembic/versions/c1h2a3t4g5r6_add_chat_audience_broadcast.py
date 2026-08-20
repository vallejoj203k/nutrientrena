"""Grupos de chat por regla y de difusión

Dos columnas en chat_conversations:

  · audience  — si el grupo se define por una REGLA ("mis clientes", "mis
    coaches") en vez de por una lista fija. NULL = lista hecha a mano.
  · broadcast — solo escribe quien lo creó; los demás responden en privado.

Revision ID: c1h2a3t4g5r6
Revises: x5i6n7v8i9t0
"""
from alembic import op
import sqlalchemy as sa

revision = "c1h2a3t4g5r6"
down_revision = "x5i6n7v8i9t0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_conversations", sa.Column("audience", sa.String(length=30), nullable=True))
    op.add_column("chat_conversations",
                  sa.Column("broadcast", sa.Boolean(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("chat_conversations", "broadcast")
    op.drop_column("chat_conversations", "audience")
