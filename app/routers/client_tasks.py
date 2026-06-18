from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, timedelta, datetime

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.client_task import ClientTask

router = APIRouter(prefix="/client-tasks", tags=["Client Tasks"])

VALID_TYPES = {"rutina","cardio","descanso","nutricion","checkin","foto","mensaje","video","sesion"}


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _out(t: ClientTask) -> dict:
    return {
        "id": t.id,
        "client_user_detail_id": t.client_user_detail_id,
        "task_type": t.task_type,
        "title": t.title,
        "notes": t.notes,
        "done": t.done,
        "week_date": t.week_date.isoformat() if t.week_date else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


class TaskCreate(BaseModel):
    client_user_detail_id: str
    task_type: str
    title: Optional[str] = None
    notes: Optional[str] = None
    week_date: Optional[date] = None   # defaults to current week's Monday


class TaskUpdate(BaseModel):
    task_type: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    done: Optional[bool] = None
    week_date: Optional[date] = None


@router.get("/client/{client_user_detail_id}", summary="Tareas del cliente", description="Retorna las tareas asignadas a un cliente, opcionalmente filtradas por semana.")
def list_for_client(
    client_user_detail_id: str,
    week: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    q = db.query(ClientTask).filter(ClientTask.client_user_detail_id == client_user_detail_id)
    if week:
        mon = _monday(week)
        q = q.filter(ClientTask.week_date == mon)
    tasks = q.order_by(ClientTask.week_date.desc(), ClientTask.id).all()
    return send_response([_out(t) for t in tasks], "OK")


@router.get("/week", summary="Tareas por semana", description="Retorna todas las tareas de la semana agrupadas por cliente.")
def bulk_by_week(
    week: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    """Return all tasks for a given week grouped by client_user_detail_id."""
    mon = _monday(week or date.today())
    tasks = db.query(ClientTask).filter(ClientTask.week_date == mon).all()
    grouped: dict = {}
    for t in tasks:
        grouped.setdefault(t.client_user_detail_id, []).append(_out(t))
    return send_response(grouped, "OK")


@router.post("", summary="Crear tarea", description="Crea una nueva tarea semanal para un cliente (rutina, cardio, nutrición, etc.).")
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    if data.task_type not in VALID_TYPES:
        return send_error(f"Tipo inválido. Válidos: {', '.join(sorted(VALID_TYPES))}")
    week = _monday(data.week_date or date.today())
    t = ClientTask(
        client_user_detail_id=data.client_user_detail_id,
        task_type=data.task_type,
        title=data.title,
        notes=data.notes,
        done=False,
        week_date=week,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return send_response(_out(t), "Tarea creada")


@router.put("/{id}", summary="Actualizar tarea", description="Modifica o marca como completada una tarea del cliente.")
def update_task(
    id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    t = db.query(ClientTask).filter(ClientTask.id == id).first()
    if not t:
        return send_error("Tarea no encontrada")
    if data.task_type and data.task_type not in VALID_TYPES:
        return send_error("Tipo inválido")
    for f, v in data.model_dump(exclude_unset=True).items():
        if f == "week_date" and v:
            v = _monday(v)
        setattr(t, f, v)
    db.commit()
    db.refresh(t)
    return send_response(_out(t), "Tarea actualizada")


@router.delete("/{id}", summary="Eliminar tarea", description="Elimina una tarea asignada a un cliente.")
def delete_task(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    t = db.query(ClientTask).filter(ClientTask.id == id).first()
    if not t:
        return send_error("Tarea no encontrada")
    db.delete(t)
    db.commit()
    return send_response(None, "Tarea eliminada")
