from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.session_log import WorkoutSession

router = APIRouter(prefix="/session-logs", tags=["Session Logs"])


class SessionCreate(BaseModel):
    client_user_detail_id: str
    routine_id: Optional[int] = None
    session_date: date
    duration_min: Optional[int] = None
    rpe: Optional[float] = None
    notes: Optional[str] = None


class SessionUpdate(BaseModel):
    routine_id: Optional[int] = None
    session_date: Optional[date] = None
    duration_min: Optional[int] = None
    rpe: Optional[float] = None
    notes: Optional[str] = None


def _out(s: WorkoutSession) -> dict:
    return {
        "id": s.id,
        "client_user_detail_id": s.client_user_detail_id,
        "routine_id": s.routine_id,
        "routine_name": s.routine.name if s.routine else None,
        "session_date": s.session_date.isoformat() if s.session_date else None,
        "duration_min": s.duration_min,
        "rpe": s.rpe,
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/client/{client_user_detail_id}")
def list_sessions(
    client_user_detail_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    sessions = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.client_user_detail_id == client_user_detail_id)
        .order_by(WorkoutSession.session_date.desc())
        .all()
    )
    return send_response([_out(s) for s in sessions], "OK")


@router.post("")
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    s = WorkoutSession(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return send_response(_out(s), "Sesión registrada")


@router.put("/{id}")
def update_session(
    id: int,
    data: SessionUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    s = db.query(WorkoutSession).filter(WorkoutSession.id == id).first()
    if not s:
        return send_error("Sesión no encontrada")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(s, f, v)
    db.commit()
    db.refresh(s)
    return send_response(_out(s), "Sesión actualizada")


@router.delete("/{id}")
def delete_session(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    s = db.query(WorkoutSession).filter(WorkoutSession.id == id).first()
    if not s:
        return send_error("Sesión no encontrada")
    db.delete(s)
    db.commit()
    return send_response(None, "Sesión eliminada")
