from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.muscle_group import MuscleGroup
from app.schemas.muscle_group import MuscleGroupCreate, MuscleGroupUpdate, MuscleGroupOut

router = APIRouter(prefix="/muscle-groups", tags=["Muscle Groups"])


def _get_or_404(db: Session, muscle_id: int) -> MuscleGroup:
    obj = db.query(MuscleGroup).filter(MuscleGroup.id == muscle_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Grupo muscular no encontrado")
    return obj


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(MuscleGroup).filter(MuscleGroup.state == 1).all()
    return [MuscleGroupOut.model_validate(i) for i in items]


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(MuscleGroup)
    if search:
        q = q.filter(MuscleGroup.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "data": [MuscleGroupOut.model_validate(i) for i in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "last_page": (total + per_page - 1) // per_page,
    }


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return MuscleGroupOut.model_validate(_get_or_404(db, id))


@router.post("")
def create(data: MuscleGroupCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = MuscleGroup(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return MuscleGroupOut.model_validate(obj)


@router.put("/{id}/update")
def updated(id: int, data: MuscleGroupUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return MuscleGroupOut.model_validate(obj)
