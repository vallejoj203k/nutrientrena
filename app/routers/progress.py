from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.progress_day import ProgressDay
from app.models.client_target import ClientTarget
from app.schemas.progress import ProgressCreate, ProgressOut, ClientTargetCreate, ClientTargetOut

router_progress = APIRouter(prefix="/progress-day-users", tags=["Progress"])
router_targets = APIRouter(prefix="/client-targets", tags=["Client Targets"])


@router_progress.post("")
def create_progress(data: ProgressCreate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = ProgressDay(user_id=data.user_id or current_user.id, **data.model_dump(exclude={"user_id"}))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(ProgressOut.model_validate(obj).model_dump(), "Progreso registrado")


@router_progress.get("/search")
def search_progress(
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    uid = user_id or current_user.id
    items = db.query(ProgressDay).filter(ProgressDay.user_id == uid).order_by(ProgressDay.date.desc()).all()
    return send_response([ProgressOut.model_validate(i).model_dump() for i in items], "OK")


@router_progress.delete("/delete/{id}")
def delete_progress(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = db.query(ProgressDay).filter(ProgressDay.id == id).first()
    if not obj:
        return send_error("Registro no encontrado")
    db.delete(obj)
    db.commit()
    return send_response(None, "Registro eliminado")


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
def create_or_update_target(data: ClientTargetCreate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
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
