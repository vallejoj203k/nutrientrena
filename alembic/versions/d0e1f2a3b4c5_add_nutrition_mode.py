"""Modo de programación de la nutrición

Dos formas de darle de comer a un cliente: un plan semanal que se repite, o el
calendario día a día. Antes convivían sin decirlo, y el cliente veía siempre el
plan semanal aunque el coach hubiera programado el calendario.

Ahora solo uno está activo. El otro NO se borra: queda en pausa.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""
import sqlalchemy as sa
from alembic import op

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def _columnas(bind):
    return {c["name"] for c in sa.inspect(bind).get_columns("user_details")}


def upgrade():
    bind = op.get_bind()
    if "nutrition_mode" not in _columnas(bind):
        op.add_column("user_details",
                      sa.Column("nutrition_mode", sa.String(20), nullable=True))
        # Lo que había hasta ahora era el plan semanal: nadie cambia de modo por
        # desplegar esto.
        op.execute("UPDATE user_details SET nutrition_mode = 'semanal' "
                   "WHERE nutrition_mode IS NULL")


def downgrade():
    bind = op.get_bind()
    if "nutrition_mode" in _columnas(bind):
        op.drop_column("user_details", "nutrition_mode")
