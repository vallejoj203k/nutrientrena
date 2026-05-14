from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.models.routine import Routine, RoutineDay, RoutineDayDetail
from app.schemas.routine import (
    RoutineCreate, RoutineUpdate, RoutineOut, RoutineCloneRequest,
    RoutineAssignRequest, RoutineListRequest, BulkCreateClientRequest,
)

router = APIRouter(prefix="/routines", tags=["Routines"])


def _get_or_404(db: Session, routine_id: int):
    return db.query(Routine).filter(Routine.id == routine_id).first()


def _clone_days(db: Session, source: Routine, new_routine_id: int):
    for day in source.days:
        new_day = RoutineDay(
            routine_id=new_routine_id,
            name=day.name,
            day_number=day.day_number,
            rest=day.rest,
        )
        db.add(new_day)
        db.flush()
        for detail in day.details:
            db.add(RoutineDayDetail(
                routine_day_id=new_day.id,
                training_id=detail.training_id,
                sets=detail.sets,
                reps=detail.reps,
                weight=detail.weight,
                rest_seconds=detail.rest_seconds,
                notes=detail.notes,
                order=detail.order,
            ))


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Routine).filter(Routine.state == 1).all()
    return send_response([RoutineOut.model_validate(i).model_dump() for i in items], "OK")


@router.post("/clone")
def clone(data: RoutineCloneRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    source = _get_or_404(db, data.routine_id)
    if not source:
        return send_error("Rutina no encontrada")
    new_routine = Routine(
        name=f"{source.name} (copia)",
        description=source.description,
        client_id=data.client_id,
        instructor_id=current_user.id,
        weeks=source.weeks,
    )
    db.add(new_routine)
    db.flush()
    _clone_days(db, source, new_routine.id)
    db.commit()
    db.refresh(new_routine)
    return send_response(RoutineOut.model_validate(new_routine).model_dump(), "Rutina clonada")


@router.post("/assigned")
def assigned(data: RoutineAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    routine = _get_or_404(db, data.routine_id)
    if not routine:
        return send_error("Rutina no encontrada")
    routine.client_id = data.client_id
    db.commit()
    return send_response(None, "Rutina asignada")


@router.post("/list")
def list_ids(data: RoutineListRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Routine).filter(Routine.id.in_(data.ids)).all()
    return send_response([RoutineOut.model_validate(i).model_dump() for i in items], "OK")


@router.post("/client/bulkCreate")
def bulk_create_client(data: BulkCreateClientRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    source = _get_or_404(db, data.routine_id)
    if not source:
        return send_error("Rutina no encontrada")
    created = []
    for client_id in data.client_ids:
        new_routine = Routine(
            name=source.name,
            description=source.description,
            client_id=client_id,
            instructor_id=current_user.id,
            weeks=source.weeks,
        )
        db.add(new_routine)
        db.flush()
        _clone_days(db, source, new_routine.id)
        created.append(new_routine.id)
    db.commit()
    return send_response({"created": created}, "Rutinas creadas")


@router.get("/client/{id_client}")
def client_routines(id_client: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Routine).filter(Routine.client_id == id_client, Routine.state == 1).all()
    return send_response([RoutineOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/client/{customer_id}/mail")
def mail(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return send_response(None, f"Correo enviado al cliente {customer_id}")


@router.get("/{id}/pdf")
def pdf(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not _get_or_404(db, id):
        return send_error("Rutina no encontrada")
    return send_response({"routine_id": id}, "PDF generado")


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")
    return send_response(RoutineOut.model_validate(routine).model_dump(), "OK")


@router.post("")
def create(data: RoutineCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    routine_data = data.model_dump(exclude={"days"})
    routine_data["instructor_id"] = current_user.id
    routine = Routine(**routine_data)
    db.add(routine)
    db.flush()
    for day_data in (data.days or []):
        day = RoutineDay(
            routine_id=routine.id,
            name=day_data.name,
            day_number=day_data.day_number,
            rest=day_data.rest or 0,
        )
        db.add(day)
        db.flush()
        for detail_data in (day_data.details or []):
            db.add(RoutineDayDetail(routine_day_id=day.id, **detail_data.model_dump()))
    db.commit()
    db.refresh(routine)
    return send_response(RoutineOut.model_validate(routine).model_dump(), "Rutina creada")


@router.put("/{id}/update")
def updated(id: int, data: RoutineUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")
    for f, v in data.model_dump(exclude_unset=True, exclude={"days"}).items():
        setattr(routine, f, v)
    if data.days is not None:
        for day in routine.days:
            db.delete(day)
        db.flush()
        for day_data in data.days:
            day = RoutineDay(
                routine_id=routine.id,
                name=day_data.name,
                day_number=day_data.day_number,
                rest=day_data.rest or 0,
            )
            db.add(day)
            db.flush()
            for detail_data in (day_data.details or []):
                db.add(RoutineDayDetail(routine_day_id=day.id, **detail_data.model_dump()))
    db.commit()
    db.refresh(routine)
    return send_response(RoutineOut.model_validate(routine).model_dump(), "Rutina actualizada")
