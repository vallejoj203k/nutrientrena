from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.models.nutrition.aliment import Aliment
from app.schemas.nutrition.aliment import AlimentCreate, AlimentUpdate, AlimentOut

router = APIRouter(prefix="/aliments", tags=["Nutrition - Aliments"])


def _get_or_404(db: Session, obj_id: str):
    return db.query(Aliment).filter(Aliment.id == obj_id).first()


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Aliment).filter(Aliment.parent_id.is_(None)).all()
    return send_response([AlimentOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    group_food_id: Optional[int] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Aliment).filter(Aliment.parent_id.is_(None))
    if search:
        q = q.filter(Aliment.name.ilike(f"%{search}%"))
    if group_food_id:
        q = q.filter(Aliment.group_food_id == group_food_id)
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [AlimentOut.model_validate(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": max(1, (total + per_page - 1) // per_page),
        },
        "OK",
    )


@router.get("/{id}/edit")
def edit(id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    return send_response(AlimentOut.model_validate(obj).model_dump(), "OK")


@router.post("")
def create(
    data: AlimentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = Aliment(**data.model_dump(), created_user_id=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(AlimentOut.model_validate(obj).model_dump(), "Alimento creado")


@router.put("/{id}/update")
def updated(
    id: str,
    data: AlimentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    obj.updated_user_id = current_user.id
    db.commit()
    db.refresh(obj)
    return send_response(AlimentOut.model_validate(obj).model_dump(), "Actualizado")


@router.post("/import")
async def import_aliments(file: UploadFile = File(...), _=Depends(get_current_user)):
    return send_response({"filename": file.filename}, "Importación recibida")
