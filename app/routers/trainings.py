from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.training import Training, TrainingClient
from app.schemas.training import TrainingCreate, TrainingUpdate, TrainingAssignRequest, TrainingOut

router = APIRouter(prefix="/trainings", tags=["Trainings"])


def _get_or_404(db: Session, training_id: int):
    return db.query(Training).filter(Training.id == training_id).first()


@router.get("/findAll", summary="Listar ejercicios", description="Retorna todos los ejercicios activos del catálogo.")
def find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    items = db.query(Training).filter(Training.state == 1).all()
    return send_response([TrainingOut.from_orm_training(i).model_dump() for i in items], "OK")


@router.get("/search", summary="Buscar ejercicios", description="Búsqueda paginada de ejercicios con filtro por nombre o grupo muscular.")
def search(
    search: Optional[str] = Query(None),
    muscle_group_id: Optional[int] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(Training)
    if search:
        q = q.filter(Training.name.ilike(f"%{search}%"))
    if muscle_group_id:
        q = q.filter(Training.muscle_group_id == muscle_group_id)
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [TrainingOut.from_orm_training(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": (total + per_page - 1) // per_page,
        },
        "OK",
    )


@router.post("/assign", summary="Asignar ejercicios a usuario", description="Asigna múltiples ejercicios a un usuario específico.")
def assigned(data: TrainingAssignRequest, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    for training_id in data.training_ids:
        exists = db.query(TrainingClient).filter_by(training_id=training_id, user_id=data.user_id).first()
        if not exists:
            db.add(TrainingClient(training_id=training_id, user_id=data.user_id))
    db.commit()
    return send_response(None, "Ejercicios asignados")


@router.get("/{id}/edit", summary="Ver ejercicio", description="Retorna el detalle de un ejercicio por su ID.")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Ejercicio no encontrado")
    return send_response(TrainingOut.from_orm_training(obj).model_dump(), "OK")


def _apply_secondary_ids(payload: dict):
    """Normalize secondary_muscle_group_ids (list) into the CSV column + single id."""
    if "secondary_muscle_group_ids" in payload:
        ids = payload.pop("secondary_muscle_group_ids") or []
        payload["secondary_muscle_group_ids"] = ",".join(str(i) for i in ids) if ids else None
        payload["secondary_muscle_group_id"] = ids[0] if ids else None
    return payload


@router.post("", summary="Crear ejercicio", description="Agrega un nuevo ejercicio al catálogo.")
def create(data: TrainingCreate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = Training(**_apply_secondary_ids(data.model_dump()))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(TrainingOut.from_orm_training(obj).model_dump(), "Ejercicio creado")


@router.put("/{id}/update", summary="Actualizar ejercicio", description="Modifica los datos de un ejercicio existente.")
def updated(id: int, data: TrainingUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Ejercicio no encontrado")
    for f, v in _apply_secondary_ids(data.model_dump(exclude_unset=True)).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(TrainingOut.from_orm_training(obj).model_dump(), "Actualizado")


@router.delete("/{id}", summary="Eliminar ejercicio", description="Elimina un ejercicio del catálogo.")
def delete(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Ejercicio no encontrado")
    # Detach references so FKs don't block the delete (routine history is kept)
    from app.models.routine import RoutineDayDetail
    db.query(RoutineDayDetail).filter(RoutineDayDetail.training_id == id).update({"training_id": None})
    db.query(TrainingClient).filter(TrainingClient.training_id == id).delete()
    db.delete(obj)
    db.commit()
    return send_response(None, "Ejercicio eliminado")
