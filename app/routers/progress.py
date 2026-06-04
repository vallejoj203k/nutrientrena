from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.progress_day import ProgressDay
from app.models.client_target import ClientTarget
from app.schemas.progress import ProgressCreate, ProgressOut, ClientTargetCreate, ClientTargetOut

router_progress = APIRouter(prefix="/progress-day-users", tags=["Progress"])
router_targets = APIRouter(prefix="/client-targets", tags=["Client Targets"])


def _out(obj: ProgressDay) -> dict:
    return ProgressOut.model_validate(obj).model_dump()


@router_progress.post("/upsert")
def upsert_progress(
    data: ProgressCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    """Create or update a progress record for a given user + date."""
    uid = data.user_id or current_user.id
    obj = db.query(ProgressDay).filter(
        ProgressDay.user_id == uid,
        ProgressDay.date == data.date,
    ).first()
    if obj:
        for f, v in data.model_dump(exclude_unset=True, exclude={"user_id"}).items():
            setattr(obj, f, v)
    else:
        obj = ProgressDay(user_id=uid, **data.model_dump(exclude={"user_id"}))
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(_out(obj), "Progreso guardado")


@router_progress.post("")
def create_progress(
    data: ProgressCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    obj = ProgressDay(user_id=data.user_id or current_user.id, **data.model_dump(exclude={"user_id"}))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(_out(obj), "Progreso registrado")


@router_progress.get("/search")
def search_progress(
    user_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    uid = user_id or current_user.id
    q = db.query(ProgressDay).filter(ProgressDay.user_id == uid)
    if from_date:
        q = q.filter(ProgressDay.date >= from_date)
    if to_date:
        q = q.filter(ProgressDay.date <= to_date)
    items = q.order_by(ProgressDay.date.desc()).all()
    return send_response([_out(i) for i in items], "OK")


@router_progress.get("/{id}")
def get_progress(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    obj = db.query(ProgressDay).filter(ProgressDay.id == id).first()
    if not obj:
        return send_error("Registro no encontrado")
    return send_response(_out(obj), "OK")


@router_progress.put("/{id}")
def update_progress(
    id: int,
    data: ProgressCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    obj = db.query(ProgressDay).filter(ProgressDay.id == id).first()
    if not obj:
        return send_error("Registro no encontrado")
    for f, v in data.model_dump(exclude_unset=True, exclude={"user_id"}).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(_out(obj), "Progreso actualizado")


@router_progress.delete("/delete/{id}")
def delete_progress(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    obj = db.query(ProgressDay).filter(ProgressDay.id == id).first()
    if not obj:
        return send_error("Registro no encontrado")
    db.delete(obj)
    db.commit()
    return send_response(None, "Registro eliminado")


# ── Client targets ────────────────────────────────────────────────────────────

@router_targets.get("/search")
def search_targets(
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    uid = user_id or current_user.id
    obj = db.query(ClientTarget).filter(ClientTarget.user_id == uid).first()
    if not obj:
        return send_response(None, "Sin objetivos registrados")
    return send_response(ClientTargetOut.model_validate(obj).model_dump(), "OK")


@router_targets.put("")
def create_or_update_target(
    data: ClientTargetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    uid = data.user_id or current_user.id
    obj = db.query(ClientTarget).filter(ClientTarget.user_id == uid).first()
    if obj:
        for f, v in data.model_dump(exclude_unset=True, exclude={"user_id"}).items():
            setattr(obj, f, v)
    else:
        obj = ClientTarget(user_id=uid, **data.model_dump(exclude={"user_id"}))
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(ClientTargetOut.model_validate(obj).model_dump(), "Objetivos actualizados")
