"""unify progress_day_users into weekly_checkins

Adds muscle_mass/photo2/photo3 to weekly_checkins and migrates existing
progress_day_users rows into weekly_checkins so both progress views share
one source.

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-07-07
"""
import uuid
from alembic import op
import sqlalchemy as sa

revision = 'b1c2d3e4f5a6'
down_revision = 'a0b1c2d3e4f5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('weekly_checkins', sa.Column('muscle_mass', sa.Float(), nullable=True))
    op.add_column('weekly_checkins', sa.Column('photo2', sa.String(500), nullable=True))
    op.add_column('weekly_checkins', sa.Column('photo3', sa.String(500), nullable=True))

    # ── Migrate existing progress_day_users rows into weekly_checkins ──
    conn = op.get_bind()
    # map user_id -> user_detail id
    details = conn.execute(sa.text("SELECT id, user_id FROM user_details")).fetchall()
    uid_to_detail = {r[1]: r[0] for r in details}

    try:
        rows = conn.execute(sa.text(
            "SELECT user_id, date, weight, body_fat, muscle_mass, waist, hip, chest, "
            "arm, thigh, notes, photo, photo2, photo3 FROM progress_day_users"
        )).fetchall()
    except Exception:
        rows = []

    ins = sa.text(
        "INSERT INTO weekly_checkins "
        "(id, client_user_detail_id, coach_user_detail_id, checkin_date, weight, notes, "
        " photo_url, photo2, photo3, body_fat, muscle_mass, waist, chest, hips, arms, legs) "
        "VALUES (:id, :cid, NULL, :d, :w, :n, :p, :p2, :p3, :bf, :mm, :wa, :ch, :hi, :ar, :le)"
    )
    for r in rows:
        (user_id, date, weight, body_fat, muscle_mass, waist, hip, chest,
         arm, thigh, notes, photo, photo2, photo3) = r
        detail_id = uid_to_detail.get(user_id)
        if not detail_id or not date:
            continue
        conn.execute(ins, {
            "id": str(uuid.uuid4()), "cid": detail_id, "d": date, "w": weight, "n": notes,
            "p": photo, "p2": photo2, "p3": photo3, "bf": body_fat, "mm": muscle_mass,
            "wa": waist, "ch": chest, "hi": hip, "ar": arm, "le": thigh,
        })


def downgrade():
    op.drop_column('weekly_checkins', 'photo3')
    op.drop_column('weekly_checkins', 'photo2')
    op.drop_column('weekly_checkins', 'muscle_mass')
