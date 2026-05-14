from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.nutrition.aliment import Aliment
from app.schemas.nutrition.aliment import AlimentCreate, AlimentUpdate, AlimentOut

router = APIRouter(prefix="/aliments", tags=["Nutrition - Aliments"])


def _get_or_404(db: Session, obj_id: int) -> Aliment:
    obj = db.query(Aliment).filter(Aliment.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Alimento no encontrado")
    return obj


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [AlimentOut.model_validate(i) for i in db.query(Aliment).filter(Aliment.state == 1).all()]


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    type_food_id: Optional[int] = Query(None),
    group_food_id: Optional[int] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Aliment)
    if search:
        q = q.filter(Aliment.name.ilike(f"%{search}%"))
    if type_food_id:
        q = q.filter(Aliment.type_food_id == type_food_id)
    if group_food_id:
        q = q.filter(Aliment.group_food_id == group_food_id)
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {"data": [AlimentOut.model_validate(i) for i in items], "total": total, "page": page, "per_page": per_page, "last_page": (total + per_page - 1) // per_page}


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return AlimentOut.model_validate(_get_or_404(db, id))


@router.post("")
def create(data: AlimentCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = Aliment(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return AlimentOut.model_validate(obj)


@router.put("/{id}/update")
def updated(id: int, data: AlimentUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return AlimentOut.model_validate(obj)


@router.post("/import")
async def import_aliments(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return {"message": "Importación recibida", "filename": file.filename}
