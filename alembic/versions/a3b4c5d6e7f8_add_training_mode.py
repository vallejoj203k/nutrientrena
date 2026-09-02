"""Modo de programación del entrenamiento

El espejo de `nutrition_mode`, para los entrenos: un plan semanal que se repite
o el calendario día a día. Van por separado a propósito — un coach puede tener
la nutrición cerrada en un plan fijo y los entrenos programados día a día, o al
revés. Un solo interruptor para las dos cosas obligaría a llevarlas igual.

El otro modo NO se borra: queda en pausa.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
"""
import sqlalchemy as sa
from alembic import op

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def _columnas(bind):
    return {c["name"] for c in sa.inspect(bind).get_columns("user_details")}


def upgrade():
    bind = op.get_bind()
    if "training_mode" not in _columnas(bind):
        op.add_column("user_details",
                      sa.Column("training_mode", sa.String(20), nullable=True))
        # Lo que había hasta ahora era el plan semanal: nadie cambia de modo por
        # desplegar esto.
        op.execute("UPDATE user_details SET training_mode = 'semanal' "
                   "WHERE training_mode IS NULL")


def downgrade():
    bind = op.get_bind()
    if "training_mode" in _columnas(bind):
        op.drop_column("user_details", "training_mode")
