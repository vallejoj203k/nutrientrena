"""add performance indexes for hot query paths

Revision ID: m1n2o3p4q5r6
Revises: l1m2n3o4p5q6
Create Date: 2026-06-08

Covers the most frequently queried columns identified in Fase 5 review:
  - event_users  : user_id, start_date
  - progress_day_users : user_id, date
  - note_users   : user_id, instructor_id
  - weekly_checkins : client_user_detail_id, checkin_date
  - role_user    : user_id  (used on every authenticated request)
  - user_details : user_id  (join on every auth lookup)
"""
from alembic import op
from sqlalchemy import inspect, text


# revision identifiers
revision = "m1n2o3p4q5r6"
down_revision = "l1m2n3o4p5q6"
branch_labels = None
depends_on = None

# (index_name, table, columns)
INDEXES = [
    ("ix_event_users_user_id",        "event_users",         ["user_id"]),
    ("ix_event_users_start_date",     "event_users",         ["start_date"]),
    ("ix_progress_day_users_user_id", "progress_day_users",  ["user_id"]),
    ("ix_progress_day_users_date",    "progress_day_users",  ["date"]),
    ("ix_note_users_user_id",         "note_users",          ["user_id"]),
    ("ix_note_users_instructor_id",   "note_users",          ["instructor_id"]),
    ("ix_weekly_checkins_client_id",  "weekly_checkins",     ["client_user_detail_id"]),
    ("ix_weekly_checkins_date",       "weekly_checkins",     ["checkin_date"]),
    ("ix_role_user_user_id",          "role_user",           ["user_id"]),
    ("ix_user_details_user_id",       "user_details",        ["user_id"]),
]


def _existing_indexes(bind, table: str) -> set[str]:
    try:
        return {idx["name"] for idx in inspect(bind).get_indexes(table)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    for name, table, cols in INDEXES:
        existing = _existing_indexes(bind, table)
        if name not in existing:
            op.create_index(name, table, cols)


def downgrade() -> None:
    bind = op.get_bind()
    for name, table, _ in INDEXES:
        existing = _existing_indexes(bind, table)
        if name in existing:
            op.drop_index(name, table_name=table)
