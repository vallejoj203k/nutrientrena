"""Puntuaciones del check-in y marca de revisado

Cinco columnas en weekly_checkins:

  · energy / effort / hunger / sleep — cómo se ha sentido el cliente, de 0 a 10.
    La ficha del cliente ya las pintaba desde hace tiempo y siempre salían "—"
    porque el campo no existía.
  · reviewed_at / reviewed_by_user_detail_id — cuándo lo revisó el coach. Antes
    solo se sabía si había escrito notas, y "lo he leído y está bien" no deja
    notas: la bandeja no podía separar lo pendiente de lo atendido.

Revision ID: c2h3e4c5k6i7
Revises: c1h2a3t4g5r6
"""
from alembic import op
import sqlalchemy as sa

revision = "c2h3e4c5k6i7"
down_revision = "c1h2a3t4g5r6"
branch_labels = None
depends_on = None


def upgrade():
    for col in ("energy", "effort", "hunger", "sleep"):
        op.add_column("weekly_checkins", sa.Column(col, sa.Integer(), nullable=True))
    op.add_column("weekly_checkins", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("weekly_checkins",
                  sa.Column("reviewed_by_user_detail_id", sa.String(length=36), nullable=True))


def downgrade():
    op.drop_column("weekly_checkins", "reviewed_by_user_detail_id")
    op.drop_column("weekly_checkins", "reviewed_at")
    for col in ("sleep", "hunger", "effort", "energy"):
        op.drop_column("weekly_checkins", col)
