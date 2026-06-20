from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.client_exercise import ClientExercise
from app.schemas.client_exercise import ClientExerciseCreate, ClientExerciseUpdate, ClientExerciseOut

router = APIRouter(prefix="/client-exercises", tags=["Client Exercises"])


def _get_or_404(db: Session, obj_id: int):
    return db.query(ClientExercise).filter(ClientExercise.id == obj_id).first()


@router.get("/findAll", summary="Listar ejercicios del cliente", description="Retorna todos los ejercicios personalizados de un cliente.")
def find_all(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    items = db.query(ClientExercise).filter(ClientExercise.client_id == client_id).order_by(ClientExercise.name).all()
    return send_response([ClientExerciseOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search", summary="Buscar ejercicios del cliente", description="Búsqueda paginada de ejercicios personalizados de un cliente por nombre y/o grupo muscular.")
def search(
    client_id: int = Query(...),
    search: Optional[str] = Query(None),
    muscle_group_id: Optional[int] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    q = db.query(ClientExercise).filter(ClientExercise.client_id == client_id)
    if search:
        q = q.filter(ClientExercise.name.ilike(f"%{search}%"))
    if muscle_group_id:
        q = q.filter(ClientExercise.muscle_group_id == muscle_group_id)
    total = q.count()
    items = q.order_by(ClientExercise.name).offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [ClientExerciseOut.model_validate(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": max(1, (total + per_page - 1) // per_page),
        },
        "OK",
    )


@router.get("/{id}/edit", summary="Ver ejercicio del cliente", description="Retorna el detalle de un ejercicio personalizado de un cliente.")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Ejercicio no encontrado")
    return send_response(ClientExerciseOut.model_validate(obj).model_dump(), "OK")


@router.post("", summary="Crear ejercicio del cliente", description="Crea un ejercicio personalizado para un cliente específico.")
def create(
    data: ClientExerciseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    payload = data.model_dump()
    obj = ClientExercise(**payload, created_user_id=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(ClientExerciseOut.model_validate(obj).model_dump(), "Ejercicio creado")


@router.put("/{id}/update", summary="Actualizar ejercicio del cliente", description="Modifica los datos de un ejercicio personalizado de un cliente.")
def update(
    id: int,
    data: ClientExerciseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Ejercicio no encontrado")

    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    obj.updated_user_id = current_user.id

    db.commit()
    db.refresh(obj)
    return send_response(ClientExerciseOut.model_validate(obj).model_dump(), "Actualizado")


@router.delete("/{id}", summary="Eliminar ejercicio del cliente", description="Elimina un ejercicio personalizado de un cliente.")
def delete(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Ejercicio no encontrado")
    try:
        db.delete(obj)
        db.commit()
    except Exception:
        db.rollback()
        return send_error("No se puede eliminar el ejercicio")
    return send_response(None, "Ejercicio eliminado")
