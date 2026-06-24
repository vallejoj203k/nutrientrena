from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, verify_client_access, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.nutrition.client_aliment import ClientAliment
from app.schemas.nutrition.client_aliment import ClientAlimentCreate, ClientAlimentUpdate, ClientAlimentOut

router = APIRouter(prefix="/client-aliments", tags=["Nutrition - Client Aliments"])


def _get_or_404(db: Session, obj_id: str):
    return db.query(ClientAliment).filter(ClientAliment.id == obj_id).first()


@router.get("/findAll", summary="Listar alimentos del cliente", description="Retorna todos los alimentos personalizados de un cliente.")
def find_all(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.models.user import UserDetail
    # client_id here is the users.id; resolve to user_details.id for access check
    detail = db.query(UserDetail).filter(UserDetail.user_id == client_id).first()
    if detail:
        verify_client_access(detail.id, current_user, db)
    items = db.query(ClientAliment).filter(ClientAliment.client_id == client_id).all()
    return send_response([ClientAlimentOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search", summary="Buscar alimentos del cliente", description="Búsqueda paginada de alimentos personalizados de un cliente por nombre.")
def search(
    client_id: int = Query(...),
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    q = db.query(ClientAliment).filter(ClientAliment.client_id == client_id)
    if search:
        q = q.filter(ClientAliment.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(ClientAliment.name).offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [ClientAlimentOut.model_validate(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": max(1, (total + per_page - 1) // per_page),
        },
        "OK",
    )


@router.get("/{id}/edit", summary="Ver alimento del cliente", description="Retorna el detalle de un alimento personalizado de un cliente.")
def edit(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    return send_response(ClientAlimentOut.model_validate(obj).model_dump(), "OK")


@router.post("", summary="Crear alimento del cliente", description="Crea un alimento personalizado para un cliente específico.")
def create(
    data: ClientAlimentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    payload = data.model_dump()
    obj = ClientAliment(**payload, created_user_id=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(ClientAlimentOut.model_validate(obj).model_dump(), "Alimento creado")


@router.put("/{id}/update", summary="Actualizar alimento del cliente", description="Modifica los datos de un alimento personalizado de un cliente.")
def update(
    id: str,
    data: ClientAlimentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")

    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    obj.updated_user_id = current_user.id

    db.commit()
    db.refresh(obj)
    return send_response(ClientAlimentOut.model_validate(obj).model_dump(), "Actualizado")


@router.delete("/{id}", summary="Eliminar alimento del cliente", description="Elimina un alimento personalizado de un cliente.")
def delete(
    id: str,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    try:
        db.delete(obj)
        db.commit()
    except Exception:
        db.rollback()
        return send_error("No se puede eliminar el alimento")
    return send_response(None, "Alimento eliminado")
