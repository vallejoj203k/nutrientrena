from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.nutrition.group_food import GroupFood
from app.schemas.nutrition.food import GroupFoodCreate, GroupFoodUpdate, GroupFoodOut

router = APIRouter(prefix="/groupFood", tags=["Nutrition - GroupFood"])


def _get_or_404(db: Session, obj_id: int):
    return db.query(GroupFood).filter(GroupFood.id == obj_id).first()


@router.get("/findAll", summary="Listar grupos de alimentos", description="Retorna todos los grupos de alimentos activos (ej: carnes, verduras, lácteos).")
def find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    items = db.query(GroupFood).filter(GroupFood.status == 1).all()
    return send_response([GroupFoodOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search", summary="Buscar grupos de alimentos", description="Búsqueda paginada de grupos de alimentos por nombre.")
def search(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
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


@router.get("/{id}/edit", summary="Ver grupo de alimentos", description="Retorna el detalle de un grupo de alimentos por su ID.")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Grupo de alimento no encontrado")
    return send_response(GroupFoodOut.model_validate(obj).model_dump(), "OK")


@router.post("", summary="Crear grupo de alimentos", description="Agrega un nuevo grupo de alimentos al catálogo.")
def create(data: GroupFoodCreate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = GroupFood(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(GroupFoodOut.model_validate(obj).model_dump(), "Creado")


@router.put("/{id}/update", summary="Actualizar grupo de alimentos", description="Modifica los datos de un grupo de alimentos existente.")
def updated(id: int, data: GroupFoodUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Grupo de alimento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(GroupFoodOut.model_validate(obj).model_dump(), "Actualizado")
