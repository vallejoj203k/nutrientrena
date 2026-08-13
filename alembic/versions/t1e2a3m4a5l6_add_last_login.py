"""add last_login_at a users

La sección "Equipo Alzum" del panel de plataforma tiene que distinguir a quien
está invitado y todavía no ha entrado de quien ya trabaja aquí, y enseñar una
"última actividad" que sea verdad.

No había ningún rastro de eso: el backend no guardaba en ningún sitio cuándo
entró alguien por última vez. Se podría haber deducido de la actividad del
usuario (entrenamientos, check-ins), pero un editor de contenido no entrena ni
hace check-ins, así que para el equipo interno ese rastro no existe.

Se rellena en el login. Las filas anteriores se quedan en NULL, que es
exactamente lo que hay que decir de ellas: no se sabe.

Revision ID: t1e2a3m4a5l6
Revises: s0p1o2r3t4e5
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa

revision = 't1e2a3m4a5l6'
down_revision = 's0p1o2r3t4e5'
branch_labels = None
depends_on = None


def _tiene_columna(tabla, columna):
    bind = op.get_bind()
    try:
        return columna in [c['name'] for c in sa.inspect(bind).get_columns(tabla)]
    except Exception:
        return False


def upgrade():
    if not _tiene_columna('users', 'last_login_at'):
        op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))


def downgrade():
    if _tiene_columna('users', 'last_login_at'):
        op.drop_column('users', 'last_login_at')
