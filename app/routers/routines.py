from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.routine import Routine, RoutineDay, RoutineDayDetail
from app.models.user import User
from app.schemas.routine import (
    RoutineCreate, RoutineUpdate, RoutineOut, RoutineCloneRequest,
    RoutineAssignRequest, RoutineListRequest, BulkCreateClientRequest
)

router = APIRouter(prefix="/routines", tags=["Routines"])


def _get_or_404(db: Session, routine_id: int) -> Routine:
    obj = db.query(Routine).filter(Routine.id == routine_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")
    return obj


def _build_routine(db: Session, data, instructor_id: int) -> Routine:
    routine_data = data.model_dump(exclude={"days"})
    routine_data["instructor_id"] = instructor_id
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
            db.add(RoutineDayDetail(
                routine_day_id=day.id,
                **detail_data.model_dump(),
            ))
    return routine


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Routine).filter(Routine.state == 1).all()
    return [RoutineOut.model_validate(i) for i in items]


@router.post("/clone")
def clone(data: RoutineCloneRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    source = _get_or_404(db, data.routine_id)
    new_routine = Routine(
        name=f"{source.name} (copia)",
        description=source.description,
        client_id=data.client_id,
        instructor_id=current_user.id,
        weeks=source.weeks,
    )
    db.add(new_routine)
    db.flush()
    for day in source.days:
        new_day = RoutineDay(routine_id=new_routine.id, name=day.name, day_number=day.day_number, rest=day.rest)
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
    db.commit()
    db.refresh(new_routine)
    return RoutineOut.model_validate(new_routine)


@router.post("/assigned")
def assigned(data: RoutineAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    routine = _get_or_404(db, data.routine_id)
    routine.client_id = data.client_id
    db.commit()
    return {"message": "Rutina asignada"}


@router.post("/list")
def list_ids(data: RoutineListRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Routine).filter(Routine.id.in_(data.ids)).all()
    return [RoutineOut.model_validate(i) for i in items]


@router.post("/client/bulkCreate")
def bulk_create_client(data: BulkCreateClientRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    source = _get_or_404(db, data.routine_id)
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
        for day in source.days:
            new_day = RoutineDay(routine_id=new_routine.id, name=day.name, day_number=day.day_number, rest=day.rest)
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
        created.append(new_routine.id)
    db.commit()
    return {"created": created}


@router.get("/client/{id_client}")
def client_routines(id_client: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Routine).filter(Routine.client_id == id_client, Routine.state == 1).all()
    return [RoutineOut.model_validate(i) for i in items]


@router.get("/client/{customer_id}/mail")
def mail(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return {"message": f"Correo enviado al cliente {customer_id}"}


@router.get("/{id}/pdf")
def pdf(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    _get_or_404(db, id)
    return {"message": "PDF generado", "routine_id": id}


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return RoutineOut.model_validate(_get_or_404(db, id))


@router.post("")
def create(data: RoutineCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    routine = _build_routine(db, data, current_user.id)
    db.commit()
    db.refresh(routine)
    return RoutineOut.model_validate(routine)


@router.put("/{id}/update")
def updated(id: int, data: RoutineUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    routine = _get_or_404(db, id)
    update_data = data.model_dump(exclude_unset=True, exclude={"days"})
    for field, value in update_data.items():
        setattr(routine, field, value)

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
    return RoutineOut.model_validate(routine)
