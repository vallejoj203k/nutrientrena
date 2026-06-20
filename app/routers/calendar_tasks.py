"""Calendar tasks — day-specific tasks & events per client.

Unlike /client-tasks (week-based), these are anchored to a specific date
and optionally recur daily / weekly / monthly.  A 'checkin' type task can
be linked to its weekly_checkins record once the coach registers it.
"""
import calendar as _cal
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_error, send_response
from app.database import get_db
from app.models.calendar_task import CalendarTask, VALID_TASK_TYPES, COLOR_MAP
from app.models.checkin import WeeklyCheckin

router = APIRouter(prefix="/calendar-tasks", tags=["Calendar Tasks"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, _cal.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


def _next_date(d: date, recurrence: str) -> date:
    if recurrence == "daily":
        return d + timedelta(days=1)
    if recurrence == "weekly":
        return d + timedelta(weeks=1)
    if recurrence == "monthly":
        return _add_months(d, 1)
    return d


def _out(t: CalendarTask) -> dict:
    return {
        "id": t.id,
        "client_user_detail_id": t.client_user_detail_id,
        "coach_user_id": t.coach_user_id,
        "task_date": t.task_date.isoformat() if t.task_date else None,
        "task_type": t.task_type,
        "title": t.title,
        "notes": t.notes,
        "color": t.color or COLOR_MAP.get(t.task_type, "#9CA3AF"),
        "done": bool(t.done),
        "done_at": t.done_at.isoformat() if t.done_at else None,
        "recurrence": t.recurrence or "none",
        "recurrence_end_date": t.recurrence_end_date.isoformat() if t.recurrence_end_date else None,
        "recurrence_group_id": t.recurrence_group_id,
        "checkin_id": t.checkin_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _checkin_out(c: WeeklyCheckin) -> dict:
    return {
        "id": c.id,
        "checkin_date": c.checkin_date.isoformat() if c.checkin_date else None,
        "weight": c.weight,
        "body_fat": c.body_fat,
        "waist": c.waist,
        "chest": c.chest,
        "hips": c.hips,
        "arms": c.arms,
        "legs": c.legs,
        "notes": c.notes,
        "coach_notes": c.coach_notes,
        "photo_url": c.photo_url,
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    client_user_detail_id: str
    task_date: date
    task_type: str
    title: Optional[str] = None
    notes: Optional[str] = None
    color: Optional[str] = None
    recurrence: Optional[str] = "none"       # none / daily / weekly / monthly
    recurrence_end_date: Optional[date] = None


class TaskUpdate(BaseModel):
    task_date: Optional[date] = None
    task_type: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    color: Optional[str] = None
    checkin_id: Optional[str] = None


class DoneToggle(BaseModel):
    done: bool
    checkin_id: Optional[str] = None   # optionally link checkin when marking done


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get(
    "/client/{client_id}",
    summary="Tareas del cliente",
    description="Lista de tareas de un cliente, opcionalmente filtradas por rango de fechas.",
)
def list_for_client(
    client_id: str,
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    task_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    q = db.query(CalendarTask).filter(
        CalendarTask.client_user_detail_id == client_id
    )
    if start:
        q = q.filter(CalendarTask.task_date >= start)
    if end:
        q = q.filter(CalendarTask.task_date <= end)
    if task_type:
        q = q.filter(CalendarTask.task_type == task_type)
    tasks = q.order_by(CalendarTask.task_date, CalendarTask.id).all()
    return send_response([_out(t) for t in tasks], "OK")


@router.get(
    "/calendar/{client_id}",
    summary="Vista calendario del cliente",
    description=(
        "Devuelve tareas + check-ins del cliente para un rango de fechas, "
        "agrupados por fecha (YYYY-MM-DD) para renderizar en el calendario."
    ),
)
def calendar_view(
    client_id: str,
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    tasks = (
        db.query(CalendarTask)
        .filter(
            CalendarTask.client_user_detail_id == client_id,
            CalendarTask.task_date >= start,
            CalendarTask.task_date <= end,
        )
        .order_by(CalendarTask.task_date, CalendarTask.id)
        .all()
    )

    checkins = (
        db.query(WeeklyCheckin)
        .filter(
            WeeklyCheckin.client_user_detail_id == client_id,
            WeeklyCheckin.checkin_date >= start,
            WeeklyCheckin.checkin_date <= end,
        )
        .order_by(WeeklyCheckin.checkin_date)
        .all()
    )

    # Build date-keyed dict
    by_date: dict = {}

    for t in tasks:
        key = t.task_date.isoformat()
        by_date.setdefault(key, {"tasks": [], "checkins": []})
        by_date[key]["tasks"].append(_out(t))

    for c in checkins:
        key = c.checkin_date.isoformat()
        by_date.setdefault(key, {"tasks": [], "checkins": []})
        by_date[key]["checkins"].append(_checkin_out(c))

    return send_response(by_date, "OK")


@router.post(
    "",
    summary="Crear tarea de calendario",
    description=(
        "Crea una tarea en una fecha específica del cliente. "
        "Si se incluye recurrence y recurrence_end_date, genera toda la serie."
    ),
)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    if data.task_type not in VALID_TASK_TYPES:
        return send_error(f"Tipo inválido. Válidos: {', '.join(sorted(VALID_TASK_TYPES))}")

    color = data.color or COLOR_MAP.get(data.task_type, "#9CA3AF")
    recurrence = data.recurrence or "none"

    if recurrence != "none" and data.recurrence_end_date and data.recurrence_end_date > data.task_date:
        group_id = int(datetime.utcnow().timestamp() * 1000) % 2147483647
        current = data.task_date
        created = []
        while current <= data.recurrence_end_date:
            t = CalendarTask(
                client_user_detail_id=data.client_user_detail_id,
                coach_user_id=current_user.id,
                task_date=current,
                task_type=data.task_type,
                title=data.title,
                notes=data.notes,
                color=color,
                done=False,
                recurrence=recurrence,
                recurrence_end_date=data.recurrence_end_date,
                recurrence_group_id=group_id,
            )
            db.add(t)
            created.append(t)
            current = _next_date(current, recurrence)
        db.commit()
        db.refresh(created[0])
        return send_response(
            {"first": _out(created[0]), "count": len(created), "group_id": group_id},
            f"{len(created)} tareas creadas",
        )

    t = CalendarTask(
        client_user_detail_id=data.client_user_detail_id,
        coach_user_id=current_user.id,
        task_date=data.task_date,
        task_type=data.task_type,
        title=data.title,
        notes=data.notes,
        color=color,
        done=False,
        recurrence="none",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return send_response(_out(t), "Tarea creada")


@router.put(
    "/{id}",
    summary="Actualizar tarea",
    description="Modifica los campos de una tarea de calendario existente.",
)
def update_task(
    id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    t = db.query(CalendarTask).filter(CalendarTask.id == id).first()
    if not t:
        return send_error("Tarea no encontrada")
    if data.task_type and data.task_type not in VALID_TASK_TYPES:
        return send_error("Tipo inválido")
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(t, field, val)
    db.commit()
    db.refresh(t)
    return send_response(_out(t), "Tarea actualizada")


@router.patch(
    "/{id}/done",
    summary="Marcar tarea como completada / pendiente",
    description=(
        "Cambia el estado done de la tarea. "
        "Al marcarla como completada se registra done_at. "
        "Si task_type='checkin' se puede pasar checkin_id para enlazar el registro."
    ),
)
def toggle_done(
    id: int,
    data: DoneToggle,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    t = db.query(CalendarTask).filter(CalendarTask.id == id).first()
    if not t:
        return send_error("Tarea no encontrada")
    t.done = data.done
    t.done_at = datetime.utcnow() if data.done else None
    if data.checkin_id is not None:
        t.checkin_id = data.checkin_id
    db.commit()
    db.refresh(t)
    return send_response(_out(t), "Actualizado")


@router.delete(
    "/group/{group_id}",
    summary="Eliminar serie recurrente",
    description="Elimina todas las tareas de una serie recurrente (por group_id).",
)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    deleted = (
        db.query(CalendarTask)
        .filter(CalendarTask.recurrence_group_id == group_id)
        .delete()
    )
    db.commit()
    return send_response({"deleted": deleted}, f"{deleted} tareas eliminadas")


@router.delete(
    "/{id}",
    summary="Eliminar tarea",
    description="Elimina una tarea individual del calendario.",
)
def delete_task(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    t = db.query(CalendarTask).filter(CalendarTask.id == id).first()
    if not t:
        return send_error("Tarea no encontrada")
    db.delete(t)
    db.commit()
    return send_response(None, "Tarea eliminada")
