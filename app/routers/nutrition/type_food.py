from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.nutrition.type_food import TypeFood
from app.schemas.nutrition.food import TypeFoodCreate, TypeFoodUpdate, TypeFoodOut

router = APIRouter(prefix="/typeFood", tags=["Nutrition - TypeFood"])


def _get_or_404(db: Session, obj_id: int) -> TypeFood:
    obj = db.query(TypeFood).filter(TypeFood.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tipo de alimento no encontrado")
    return obj


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [TypeFoodOut.model_validate(i) for i in db.query(TypeFood).filter(TypeFood.state == 1).all()]


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(TypeFood)
    if search:
        q = q.filter(TypeFood.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {"data": [TypeFoodOut.model_validate(i) for i in items], "total": total, "page": page, "per_page": per_page, "last_page": (total + per_page - 1) // per_page}


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return TypeFoodOut.model_validate(_get_or_404(db, id))


@router.post("")
def create(data: TypeFoodCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = TypeFood(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return TypeFoodOut.model_validate(obj)


@router.put("/{id}/update")
def updated(id: int, data: TypeFoodUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return TypeFoodOut.model_validate(obj)
