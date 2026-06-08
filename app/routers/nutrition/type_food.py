from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.nutrition.type_food import TypeFood
from app.schemas.nutrition.food import TypeFoodCreate, TypeFoodUpdate, TypeFoodOut

router = APIRouter(prefix="/typeFood", tags=["Nutrition - TypeFood"])


def _get_or_404(db: Session, obj_id: int):
    return db.query(TypeFood).filter(TypeFood.id == obj_id).first()


@router.get("/findAll", summary="Listar tipos de alimento", description="Retorna todos los tipos de alimento activos (ej: proteína, carbohidrato).")
def find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    items = db.query(TypeFood).filter(TypeFood.status == 1).all()
    return send_response([TypeFoodOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search", summary="Buscar tipos de alimento", description="Búsqueda paginada de tipos de alimento por nombre.")
def search(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(TypeFood)
    if search:
        q = q.filter(TypeFood.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {"data": [TypeFoodOut.model_validate(i).model_dump() for i in items], "total": total, "page": page, "per_page": per_page, "last_page": (total + per_page - 1) // per_page},
        "OK",
    )


@router.get("/{id}/edit", summary="Ver tipo de alimento", description="Retorna el detalle de un tipo de alimento por su ID.")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Tipo de alimento no encontrado")
    return send_response(TypeFoodOut.model_validate(obj).model_dump(), "OK")


@router.post("", summary="Crear tipo de alimento", description="Agrega un nuevo tipo de alimento al catálogo.")
def create(data: TypeFoodCreate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = TypeFood(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(TypeFoodOut.model_validate(obj).model_dump(), "Creado")


@router.put("/{id}/update", summary="Actualizar tipo de alimento", description="Modifica los datos de un tipo de alimento existente.")
def updated(id: int, data: TypeFoodUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Tipo de alimento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(TypeFoodOut.model_validate(obj).model_dump(), "Actualizado")
