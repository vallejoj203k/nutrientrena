from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.nutrition.group_food import GroupFood
from app.schemas.nutrition.food import GroupFoodCreate, GroupFoodUpdate, GroupFoodOut

router = APIRouter(prefix="/groupFood", tags=["Nutrition - GroupFood"])


def _get_or_404(db: Session, obj_id: int) -> GroupFood:
    obj = db.query(GroupFood).filter(GroupFood.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Grupo de alimento no encontrado")
    return obj


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [GroupFoodOut.model_validate(i) for i in db.query(GroupFood).filter(GroupFood.state == 1).all()]


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(GroupFood)
    if search:
        q = q.filter(GroupFood.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {"data": [GroupFoodOut.model_validate(i) for i in items], "total": total, "page": page, "per_page": per_page, "last_page": (total + per_page - 1) // per_page}


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return GroupFoodOut.model_validate(_get_or_404(db, id))


@router.post("")
def create(data: GroupFoodCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = GroupFood(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return GroupFoodOut.model_validate(obj)


@router.put("/{id}/update")
def updated(id: int, data: GroupFoodUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return GroupFoodOut.model_validate(obj)
