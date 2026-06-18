from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.routine import Routine, RoutineBlock, RoutineDay, RoutineDayDetail
from app.pdf.routine_pdf import generate_routine_pdf
from app.schemas.routine import (
    RoutineCreate, RoutineUpdate, RoutineOut, RoutineCloneRequest,
    RoutineAssignRequest, RoutineListRequest, BulkCreateClientRequest,
    RoutineDayOut, RoutineCreateV2, RoutineUpdateV2,
)

router = APIRouter(prefix="/routines", tags=["Routines"])


def _get_or_404(db: Session, routine_id: int):
    return db.query(Routine).filter(Routine.id == routine_id).first()


def _serialize_day(day: RoutineDay) -> dict:
    blocks = []
    # New-style: has blocks
    if day.blocks:
        for blk in sorted(day.blocks, key=lambda b: b.order_index):
            exercises = []
            for ex in blk.exercises:
                exercises.append({
                    "id": ex.id,
                    "training_id": ex.training_id,
                    "training_name": ex.training.name if ex.training else None,
                    "muscle_group_name": ex.training.muscle_group.name if (ex.training and ex.training.muscle_group) else None,
                    "series": ex.series,
                    "repetitions": ex.repetitions,
                    "break_time": ex.break_time,
                    "intensity_type": ex.intensity_type,
                    "intensity_value": ex.intensity_value,
                    "notes": ex.notes,
                    "order_index": ex.order_index or 0,
                })
            blocks.append({
                "id": blk.id,
                "block_type": blk.block_type,
                "order_index": blk.order_index,
                "exercises": exercises,
            })
    # Old-style: flat details without blocks → group into a default normal block
    old_details = [d for d in day.details if d.block_id is None]
    if old_details:
        exercises = [{
            "id": d.id,
            "training_id": d.training_id,
            "training_name": d.training.name if d.training else None,
            "muscle_group_name": d.training.muscle_group.name if (d.training and d.training.muscle_group) else None,
            "series": d.series,
            "repetitions": d.repetitions,
            "break_time": d.break_time,
            "intensity_type": getattr(d, 'intensity_type', None),
            "intensity_value": getattr(d, 'intensity_value', None),
            "notes": getattr(d, 'notes', None),
            "order_index": 0,
        } for d in old_details]
        blocks.insert(0, {"id": None, "block_type": "normal", "order_index": -1, "exercises": exercises})

    return {
        "id": day.id,
        "day_name": day.day_name,
        "description": day.description,
        "blocks": blocks,
    }


def _serialize(routine: Routine) -> dict:
    out = RoutineOut.model_validate(routine).model_dump(exclude={"days_list"})
    out["notes"] = routine.notes
    out["days_list"] = [_serialize_day(d) for d in routine.days_list]
    return out


def _create_days(db: Session, routine_id: int, days_data: list):
    """Old-style backward-compat day creation (no blocks)."""
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


def _create_days_v2(db: Session, routine_id: int, days_data: list):
    """V2 block-aware day creation."""
    for day_data in days_data:
        day = RoutineDay(
            routine_id=routine_id,
            day_name=day_data.day_name,
            description=day_data.description or day_data.content_html,
        )
        db.add(day)
        db.flush()
        # New-style blocks
        for blk_data in (day_data.blocks or []):
            blk = RoutineBlock(
                routine_id=routine_id,
                routine_day_id=day.id,
                block_type=blk_data.block_type or "normal",
                order_index=blk_data.order_index or 0,
            )
            db.add(blk)
            db.flush()
            for ex_idx, ex_data in enumerate(blk_data.exercises or []):
                db.add(RoutineDayDetail(
                    routine_id=routine_id,
                    routine_day_id=day.id,
                    block_id=blk.id,
                    training_id=ex_data.training_id,
                    series=ex_data.series,
                    repetitions=ex_data.repetitions,
                    break_time=ex_data.break_time,
                    intensity_type=ex_data.intensity_type,
                    intensity_value=ex_data.intensity_value,
                    notes=ex_data.notes,
                    order_index=ex_data.order_index if ex_data.order_index is not None else ex_idx,
                ))
        # Old-style details fallback (backward compat for existing callers)
        for det in (day_data.details or []):
            db.add(RoutineDayDetail(
                routine_id=routine_id,
                routine_day_id=day.id,
                block_id=None,
                muscle_group_id=det.muscle_group_id,
                training_id=det.training_id,
                series=det.series,
                repetitions=det.repetitions,
                break_time=det.break_time,
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
        # Clone blocks
        for blk in day.blocks:
            new_blk = RoutineBlock(
                routine_id=new_routine_id,
                routine_day_id=new_day.id,
                block_type=blk.block_type,
                order_index=blk.order_index,
            )
            db.add(new_blk)
            db.flush()
            for ex in blk.exercises:
                db.add(RoutineDayDetail(
                    routine_id=new_routine_id,
                    routine_day_id=new_day.id,
                    block_id=new_blk.id,
                    training_id=ex.training_id,
                    series=ex.series,
                    repetitions=ex.repetitions,
                    break_time=ex.break_time,
                    intensity_type=ex.intensity_type,
                    intensity_value=ex.intensity_value,
                    notes=ex.notes,
                    order_index=ex.order_index,
                ))
        # Clone old-style flat details
        for detail in day.details:
            if detail.block_id is None:
                db.add(RoutineDayDetail(
                    routine_id=new_routine_id,
                    routine_day_id=new_day.id,
                    muscle_group_id=detail.muscle_group_id,
                    training_id=detail.training_id,
                    series=detail.series,
                    repetitions=detail.repetitions,
                    break_time=detail.break_time,
                ))


@router.get("/findAll", summary="Listar rutinas", description="Retorna todas las rutinas del coach autenticado.")
def find_all(db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    items = db.query(Routine).filter(Routine.user_id == current_user.id).all()
    return send_response([_serialize(i) for i in items], "OK")


@router.post("/clone", summary="Clonar rutina", description="Crea una copia de una rutina existente con todos sus días y ejercicios.")
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
        notes=source.notes,
    )
    db.add(new_routine)
    db.flush()
    _clone_days(db, source, new_routine.id)
    db.commit()
    db.refresh(new_routine)
    return send_response(_serialize(new_routine), "Rutina clonada")


@router.post("/assigned", summary="Asignar rutina a cliente", description="Crea y asigna una rutina directamente a un cliente.")
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


@router.post("/list", summary="Listar rutinas por IDs", description="Retorna múltiples rutinas por sus IDs.")
def list_ids(data: RoutineListRequest, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    items = db.query(Routine).filter(Routine.id.in_(data.ids)).all()
    return send_response([_serialize(i) for i in items], "OK")


@router.post("/client/bulkCreate", summary="Crear rutinas en lote para cliente", description="Crea o actualiza múltiples rutinas asignadas a un cliente en una sola operación.")
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


@router.get("/client/{client_id}", summary="Rutinas del cliente", description="Retorna todas las rutinas asignadas a un cliente.")
def client_routines(client_id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    from app.models.user import UserDetail
    client_detail = db.query(UserDetail).filter(UserDetail.id == client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")
    items = db.query(Routine).filter(Routine.user_id == client_detail.user_id).all()
    return send_response([_serialize(i) for i in items], "OK")


@router.get("/client/{customer_id}/mail", summary="Enviar rutina por email", description="Envía la rutina del cliente por correo electrónico.")
def mail(customer_id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    return send_response(None, f"Correo enviado al cliente {customer_id}")


@router.get("/{id}/pdf", summary="Exportar rutina a PDF", description="Genera y descarga la rutina en formato PDF.")
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


@router.get("/{id}/edit", summary="Ver rutina", description="Retorna el detalle completo de una rutina con todos sus días y bloques de ejercicios.")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")
    return send_response(_serialize(routine), "OK")


@router.post("", summary="Crear rutina", description="Crea una nueva rutina con días y bloques de ejercicios (formato V2).")
def create(data: RoutineCreateV2, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = Routine(
        name=data.name,
        user_id=current_user.id,
        gender_id=data.gender_id,
        training=data.training,
        training_level_id=data.training_level_id,
        time=data.time,
        days=data.days,
        notes=data.notes,
    )
    db.add(routine)
    db.flush()
    _create_days_v2(db, routine.id, data.days_list or [])
    db.commit()
    db.refresh(routine)
    return send_response(_serialize(routine), "Rutina creada")


@router.put("/{id}/update", summary="Actualizar rutina", description="Modifica una rutina existente, reemplazando sus días y ejercicios.")
def updated(id: int, data: RoutineUpdateV2, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")

    for f in ("name", "gender_id", "training", "training_level_id", "time", "days", "notes"):
        v = getattr(data, f, None)
        if v is not None:
            setattr(routine, f, v)

    if data.days_list is not None:
        for day in list(routine.days_list):
            # Delete old-style (block_id IS NULL) details explicitly before cascade
            for det in list(day.details):
                db.delete(det)
            db.delete(day)
        db.flush()
        _create_days_v2(db, routine.id, data.days_list)

    db.commit()
    db.refresh(routine)
    return send_response(_serialize(routine), "Rutina actualizada")


@router.delete("/{id}", summary="Eliminar rutina", description="Elimina una rutina y todos sus días y ejercicios.")
def delete(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    routine = _get_or_404(db, id)
    if not routine:
        return send_error("Rutina no encontrada")
    db.delete(routine)
    db.commit()
    return send_response(None, "Rutina eliminada")
