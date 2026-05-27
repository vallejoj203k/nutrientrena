from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.routine import Routine, RoutineDay, RoutineDayDetail
from app.pdf.routine_pdf import generate_routine_pdf
from app.schemas.routine import (
    RoutineCreate, RoutineUpdate, RoutineOut, RoutineCloneRequest,
    RoutineAssignRequest, RoutineListRequest, BulkCreateClientRequest,
    RoutineDayOut,
)

router = APIRouter(prefix="/routines", tags=["Routines"])


def _get_or_404(db: Session, routine_id: int):
    return db.query(Routine).filter(Routine.id == routine_id).first()


def _serialize(routine: Routine) -> dict:
    out = RoutineOut.model_validate(routine).model_dump(exclude={"days_list"})
    out["days_list"] = [RoutineDayOut.from_orm_day(d).model_dump() for d in routine.days_list]
    return out


def _create_days(db: Session, routine_id: int, days_data: list):
    for day_data in days_data:
        day = RoutineDay(
            routine_id=routine_id,
            day_name=day_data.day_name,
            description=day_data.content_html,
        )
        db.add(day)
        db.flush()
        for detail_data in (day_data.details or []):
            db.add(RoutineDayDetail(
                routine_id=routine_id,
                routine_day_id=day.id,
                muscle_group_id=detail_data.muscle_group_id,
                training_id=detail_data.training_id,
                series=detail_data.series,
                repetitions=detail_data.repetitions,
                break_time=detail_data.break_time,
            ))


def _clone_days(db: Session, source: Routine, new_routine_id: int):
    for day in source.days_list:
        new_day = RoutineDay(
            routine_id=new_routine_id,
            day_name=day.day_name,
            description=day.description,
        )
        db.add(new_day)
        db.flush()
        for detail in day.details:
            db.add(RoutineDayDetail(
                routine_id=new_routine_id,
                routine_day_id=new_day.id,
                muscle_group_id=detail.muscle_group_id,
                training_id=detail.training_id,
                series=detail.series,
                repetitions=detail.repetitions,
                break_time=detail.break_time,
            ))


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    items = db.query(Routine).filter(Routine.user_id == current_user.id).all()
    return send_response([_serialize(i) for i in items], "OK")


@router.post("/clone")
def clone(data: RoutineCloneRequest, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    source = _get_or_404(db, data.id)
    if not source:
        return send_error("Rutina no encontrada")
    new_routine = Routine(
        name=f"{source.name} (copia)",
        user_id=current_user.id,
        gender_id=source.gender_id,
        training=source.training,
        training_level_id=source.training_level_id,
        time=source.time,
        days=source.days,
    )
    db.add(new_routine)
    db.flush()
    _clone_days(db, source, new_routine.id)
    db.commit()
    db.refresh(new_routine)
    return send_response(_serialize(new_routine), "Rutina clonada")


@router.post("/assigned")
def assigned(data: RoutineAssignRequest, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    from app.models.user import UserDetail
    client_detail = db.query(UserDetail).filter(UserDetail.id == data.client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    routine = Routine(
        name=data.name,
        user_id=client_detail.user_id,
        gender_id=data.gender_id,
        training=data.training,
        training_level_id=data.training_level_id,
        time=data.time,
        days=data.days,
    )
    db.add(routine)
    db.flush()
    _create_days(db, routine.id, data.days_list or [])
    db.commit()
    db.refresh(routine)
    return send_response(_serialize(routine), "Rutina asignada")


@router.post("/list")
def list_ids(data: RoutineListRequest, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    items = db.query(Routine).filter(Routine.id.in_(data.ids)).all()
    return send_response([_serialize(i) for i in items], "OK")


@router.post("/client/bulkCreate")
def bulk_create_client(
    data: BulkCreateClientRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.models.user import UserDetail
    client_detail = db.query(UserDetail).filter(UserDetail.id == data.client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    created = []
    for routine_data in data.routines:
        if routine_data.id:
            routine = db.query(Routine).filter(Routine.id == routine_data.id).first()
            if routine:
                routine.name = routine_data.name
                routine.gender_id = routine_data.gender_id
                routine.training = routine_data.training
                routine.training_level_id = routine_data.training_level_id
                routine.time = routine_data.time
                routine.days = routine_data.days
                for day in list(routine.days_list):
                    db.delete(day)
                db.flush()
                _create_days(db, routine.id, routine_data.days_list or [])
                created.append(routine.id)
                continue

        new_routine = Routine(
            name=routine_data.name,
            user_id=client_detail.user_id,
            gender_id=routine_data.gender_id,
            training=routine_data.training,
            training_level_id=routine_data.training_level_id,
            time=routine_data.time,
            days=routine_data.days,
        )
        db.add(new_routine)
        db.flush()
        _create_days(db, new_routine.id, routine_data.days_list or [])
        created.append(new_routine.id)

    db.commit()
    return send_response({"created": created}, "Rutinas creadas")


@router.get("/client/{client_id}")
def client_routines(client_id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    from app.models.user import UserDetail
    client_detail = db.query(UserDetail).filter(UserDetail.id == client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")
    items = db.query(Routine).filter(Routine.user_id == client_detail.user_id).all()
    return send_response([_serialize(i) for i in items], "OK")


@router.get("/client/{customer_id}/mail")
def mail(customer_id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    return send_response(None, f"Correo enviado al cliente {customer_id}")


@router.get("/{id}/pdf")
def pdf(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")
    try:
        pdf_bytes = generate_routine_pdf(routine)
    except Exception as e:
        return send_error(f"Error generando PDF: {str(e)}", code=500)
    safe_name = (routine.name or "rutina").replace(" ", "_").lower()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
    )


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")
    return send_response(_serialize(routine), "OK")


@router.post("")
def create(data: RoutineCreate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = Routine(
        name=data.name,
        user_id=current_user.id,
        gender_id=data.gender_id,
        training=data.training,
        training_level_id=data.training_level_id,
        time=data.time,
        days=data.days,
    )
    db.add(routine)
    db.flush()
    _create_days(db, routine.id, data.days_list or [])
    db.commit()
    db.refresh(routine)
    return send_response(_serialize(routine), "Rutina creada")


@router.put("/{id}/update")
def updated(id: int, data: RoutineUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")

    for f in ("name", "gender_id", "training", "training_level_id", "time", "days"):
        v = getattr(data, f, None)
        if v is not None:
            setattr(routine, f, v)

    if data.days_list is not None:
        for day in list(routine.days_list):
            db.delete(day)
        db.flush()
        _create_days(db, routine.id, data.days_list)

    db.commit()
    db.refresh(routine)
    return send_response(_serialize(routine), "Rutina actualizada")


@router.delete("/{id}")
def delete(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")
    db.delete(routine)
    db.commit()
    return send_response(None, "Rutina eliminada")
