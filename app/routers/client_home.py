"""Zona del cliente — endpoint agregado para la pantalla de Inicio.

Devuelve, en una sola llamada, lo que necesita el Inicio del cliente:
perfil, coach, adherencia de la semana, sesión/rutina, estado del
check-in y contador de notificaciones.

Se calcula siempre para el usuario autenticado (ownership implícito: el
cliente solo obtiene lo suyo).
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH, CLIENT
from app.core.responses import send_response
from app.models.user import User, UserDetail, UserParent
from app.models.routine import Routine
from app.models.session_log import WorkoutSession
from app.models.checkin import WeeklyCheckin

router = APIRouter(prefix="/client", tags=["Client"])

_WEEKDAY_ES = ["L", "M", "X", "J", "V", "S", "D"]


def _client_detail(db: Session, user: User):
    return db.query(UserDetail).filter(UserDetail.user_id == user.id).first()


def _coach_of(db: Session, client_detail_id: str):
    """Coach (UserDetail) del cliente, vía user_parents. None si no tiene."""
    parent = db.query(UserParent).filter(
        UserParent.user_detail_id == client_detail_id
    ).first()
    if not parent:
        return None
    return db.query(UserDetail).filter(
        UserDetail.id == parent.parent_user_detail_id
    ).first()


@router.get("/home", summary="Inicio del cliente", description="Datos agregados de la pantalla de inicio del cliente.")
def client_home(db: Session = Depends(get_db), current_user: User = Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT))):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # lunes
    week_end = week_start + timedelta(days=6)

    detail = _client_detail(db, current_user)

    # ── Perfil ──
    full_name = current_user.name if hasattr(current_user, "name") else None
    if detail:
        full_name = (f"{detail.name or ''} {detail.last_name or ''}").strip() or full_name
    full_name = full_name or getattr(current_user, "email", None) or "Cliente"
    profile = {
        "name": full_name,
        "photo": getattr(current_user, "photo", None),
        "initials": (full_name.strip()[:1] or "C").upper(),
    }

    # ── Coach ──
    coach = None
    if detail:
        cd = _coach_of(db, detail.id)
        if cd:
            coach = {"name": (f"{cd.name or ''} {cd.last_name or ''}").strip() or "Coach"}

    # ── Adherencia de la semana (sesiones registradas por día) ──
    done_dates = set()
    if detail:
        sessions = db.query(WorkoutSession).filter(
            WorkoutSession.client_user_detail_id == detail.id,
            WorkoutSession.session_date >= week_start,
            WorkoutSession.session_date <= week_end,
        ).all()
        done_dates = {s.session_date for s in sessions}
    week = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        week.append({
            "date": d.isoformat(),
            "label": _WEEKDAY_ES[i],
            "day": d.day,
            "done": d in done_dates,
            "is_today": d == today,
        })
    week_range = f"{week_start.day}–{week_end.day} {week_end.strftime('%b')}"

    # ── Rutina asignada (mejor esfuerzo: la activa más reciente del cliente) ──
    routine = None
    r = db.query(Routine).filter(
        Routine.user_id == current_user.id
    ).order_by(Routine.id.desc()).first()
    if r:
        # "Sesión de hoy": aún no hay agenda calendario → se ofrece la rutina.
        first_day = r.days_list[0] if r.days_list else None
        routine = {
            "id": r.id,
            "name": (first_day.day_name if first_day else None) or r.name,
            "focus": r.objective or r.training or None,
            "duration_min": r.time,
            "scheduled_today": None,  # [pendiente] concepto de agenda "qué toca hoy"
        }

    # ── Check-in de la semana ──
    checkin_done = False
    if detail:
        checkin_done = db.query(WeeklyCheckin).filter(
            WeeklyCheckin.client_user_detail_id == detail.id,
            WeeklyCheckin.checkin_date >= week_start,
            WeeklyCheckin.checkin_date <= week_end,
        ).first() is not None
    checkin = {
        "status": "done" if checkin_done else "pending",
        "coach_name": coach["name"] if coach else None,
        # [pendiente] "solicitud de check-in" del coach con campos concretos:
        "requested_fields": ["peso", "fotos", "medidas"],
    }

    return send_response({
        "profile": profile,
        "coach": coach,
        "week": {"range": week_range, "days": week},
        "routine": routine,
        "menu": None,          # [pendiente] asignación menú↔cliente
        "checkin": checkin,
        "notifications_unread": 0,  # [pendiente] modelo de notificaciones
    }, "OK")


@router.get("/routines", summary="Rutinas del cliente", description="Rutinas (planes) asignadas al cliente autenticado, con sus días y ejercicios.")
def client_routines(db: Session = Depends(get_db), current_user: User = Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT))):
    # Reutiliza el serializador del panel del coach (mismo formato de días/bloques/ejercicios).
    from app.routers.routines import _serialize as _serialize_routine
    rows = db.query(Routine).filter(
        Routine.user_id == current_user.id
    ).order_by(Routine.id.desc()).all()
    return send_response([_serialize_routine(r) for r in rows], "OK")
