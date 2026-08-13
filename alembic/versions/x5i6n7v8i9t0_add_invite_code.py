"""Código de invitación para reclamar una cuenta desde el login

El flujo que pidió el cliente: quien recibe una invitación entra en la pantalla
de acceso, pulsa "Soy invitado", pone su correo y crea su contraseña. Sin
depender de que le llegue un correo.

Hace falta algo más que el correo. Con solo el correo, cualquiera que lo
conozca —o lo adivine— podría reclamar la cuenta antes que su dueño, y estamos
hablando de cuentas de super-admin. El código lo pasa quien invita por el canal
que quiera; quien invita sigue sin conocer la contraseña.

Se guarda hasheado, igual que una contraseña: en claro sería una invitación
abierta a quien leyera la base de datos. Y caduca, para que un código olvidado
en un chat no valga para siempre.

Revision ID: x5i6n7v8i9t0
Revises: w4n5o6t7a8s9
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'x5i6n7v8i9t0'
down_revision = 'w4n5o6t7a8s9'
branch_labels = None
depends_on = None


def _tiene_columna(tabla, columna):
    try:
        return columna in [c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabla)]
    except Exception:
        return False


def upgrade():
    if not _tiene_columna('users', 'invite_code_hash'):
        op.add_column('users', sa.Column('invite_code_hash', sa.String(255), nullable=True))
    if not _tiene_columna('users', 'invite_expires_at'):
        op.add_column('users', sa.Column('invite_expires_at', sa.DateTime(), nullable=True))


def downgrade():
    for c in ('invite_expires_at', 'invite_code_hash'):
        if _tiene_columna('users', c):
            op.drop_column('users', c)
