"""Adjuntos en el chat

Hasta ahora un mensaje solo podía ser texto. El coach que quería mandarle una
foto o el PDF de la dieta a su cliente tenía que salirse a WhatsApp.

`content` pasa a admitir NULL: un mensaje puede ser solo un archivo, y obligar
a escribir algo para poder mandar una foto es pedir relleno.

Revision ID: a7c8h9a0t1a2
Revises: c2h3e4c5k6i7
"""
import sqlalchemy as sa
from alembic import op

revision = "a7c8h9a0t1a2"
down_revision = "c2h3e4c5k6i7"
branch_labels = None
depends_on = None


def _columnas(bind):
    return {c["name"] for c in sa.inspect(bind).get_columns("chat_messages")}


def upgrade():
    bind = op.get_bind()
    hay = _columnas(bind)
    for nombre, tipo in (
        ("attachment_url", sa.String(500)),
        ("attachment_name", sa.String(255)),
        ("attachment_type", sa.String(100)),
        ("attachment_size", sa.Integer()),
    ):
        if nombre not in hay:
            op.add_column("chat_messages", sa.Column(nombre, tipo, nullable=True))

    # SQLite no sabe alterar columnas; en las pruebas las tablas se crean desde
    # los modelos, que ya la traen anulable.
    if bind.dialect.name != "sqlite":
        op.alter_column("chat_messages", "content",
                        existing_type=sa.Text(), nullable=True)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        # Los mensajes que son solo archivo no tienen texto: se les pone uno
        # para que la columna pueda volver a ser obligatoria sin perderlos.
        op.execute("UPDATE chat_messages SET content = '(archivo)' WHERE content IS NULL")
        op.alter_column("chat_messages", "content",
                        existing_type=sa.Text(), nullable=False)
    hay = _columnas(bind)
    for nombre in ("attachment_size", "attachment_type", "attachment_name", "attachment_url"):
        if nombre in hay:
            op.drop_column("chat_messages", nombre)
