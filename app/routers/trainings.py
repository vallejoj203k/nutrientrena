from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.models.training import Training, TrainingClient
from app.schemas.training import TrainingCreate, TrainingUpdate, TrainingAssignRequest, TrainingOut

router = APIRouter(prefix="/trainings", tags=["Trainings"])


def _get_or_404(db: Session, training_id: int):
    return db.query(Training).filter(Training.id == training_id).first()


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Training).filter(Training.state == 1).all()
    return send_response([TrainingOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    muscle_group_id: Optional[int] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Training)
    if search:
        q = q.filter(Training.name.ilike(f"%{search}%"))
    if muscle_group_id:
        q = q.filter(Training.muscle_group_id == muscle_group_id)
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [TrainingOut.model_validate(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": (total + per_page - 1) // per_page,
        },
        "OK",
    )


@router.post("/assign")
def assigned(data: TrainingAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    for training_id in data.training_ids:
        exists = db.query(TrainingClient).filter_by(training_id=training_id, user_id=data.user_id).first()
        if not exists:
            db.add(TrainingClient(training_id=training_id, user_id=data.user_id))
    db.commit()
    return send_response(None, "Ejercicios asignados")


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Ejercicio no encontrado")
    return send_response(TrainingOut.model_validate(obj).model_dump(), "OK")


@router.post("")
def create(data: TrainingCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = Training(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(TrainingOut.model_validate(obj).model_dump(), "Ejercicio creado")


@router.put("/{id}/update")
def updated(id: int, data: TrainingUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Ejercicio no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(TrainingOut.model_validate(obj).model_dump(), "Actualizado")
