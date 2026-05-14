from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.models.nutrition.group_food import GroupFood
from app.schemas.nutrition.food import GroupFoodCreate, GroupFoodUpdate, GroupFoodOut

router = APIRouter(prefix="/groupFood", tags=["Nutrition - GroupFood"])


def _get_or_404(db: Session, obj_id: int):
    return db.query(GroupFood).filter(GroupFood.id == obj_id).first()


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(GroupFood).filter(GroupFood.status == 1).all()
    return send_response([GroupFoodOut.model_validate(i).model_dump() for i in items], "OK")


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
    return send_response(
        {"data": [GroupFoodOut.model_validate(i).model_dump() for i in items], "total": total, "page": page, "per_page": per_page, "last_page": (total + per_page - 1) // per_page},
        "OK",
    )


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Grupo de alimento no encontrado")
    return send_response(GroupFoodOut.model_validate(obj).model_dump(), "OK")


@router.post("")
def create(data: GroupFoodCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = GroupFood(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(GroupFoodOut.model_validate(obj).model_dump(), "Creado")


@router.put("/{id}/update")
def updated(id: int, data: GroupFoodUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Grupo de alimento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(GroupFoodOut.model_validate(obj).model_dump(), "Actualizado")
