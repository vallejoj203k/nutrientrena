from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.muscle_group import MuscleGroup
from app.schemas.muscle_group import MuscleGroupCreate, MuscleGroupUpdate, MuscleGroupOut

router = APIRouter(prefix="/muscle-groups", tags=["Muscle Groups"])


def _get_or_404(db: Session, muscle_id: int):
    return db.query(MuscleGroup).filter(MuscleGroup.id == muscle_id).first()


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    items = db.query(MuscleGroup).filter(MuscleGroup.state == 1).all()
    return send_response([MuscleGroupOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(MuscleGroup)
    if search:
        q = q.filter(MuscleGroup.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [MuscleGroupOut.model_validate(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": (total + per_page - 1) // per_page,
        },
        "OK",
    )


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Grupo muscular no encontrado")
    return send_response(MuscleGroupOut.model_validate(obj).model_dump(), "OK")


@router.post("")
def create(data: MuscleGroupCreate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = MuscleGroup(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(MuscleGroupOut.model_validate(obj).model_dump(), "Grupo muscular creado")


@router.put("/{id}/update")
def updated(id: int, data: MuscleGroupUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Grupo muscular no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(MuscleGroupOut.model_validate(obj).model_dump(), "Actualizado")
