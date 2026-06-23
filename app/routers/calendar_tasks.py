"""Calendar tasks — day-specific tasks & events per client.

Unlike /client-tasks (week-based), these are anchored to a specific date
and optionally recur daily / weekly / monthly.  A 'checkin' type task can
be registered in one atomic call via POST /{id}/checkin, which creates the
WeeklyCheckin record and links it back to the task.

Endpoints
---------
GET  /client/{client_id}            — list (optional date range + type filter)
GET  /week/{client_id}              — week view grouped by weekday (Mon-Sun)
GET  /month/{client_id}             — month view grouped by day-of-month
GET  /calendar/{client_id}          — tasks + checkins merged, keyed by date
POST /                              — create one task or a full recurring series
POST /bulk                          — create multiple tasks in one call
POST /copy-week                     — duplicate one week's tasks to another week
POST /{id}/checkin                  — register check-in + mark task done (atomic)
PUT  /{id}                          — update task fields
PATCH /{id}/done                    — toggle done / undone
DELETE /group/{group_id}            — delete entire recurring series
DELETE /{id}                        — delete single task
"""
import calendar as _cal
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH, CLIENT
from app.core.dependencies import _user_role_ids
from app.core.responses import send_error, send_response
from app.database import get_db
from app.models.calendar_task import CalendarTask, VALID_TASK_TYPES, COLOR_MAP
from app.models.checkin import WeeklyCheckin
from app.models.user import UserDetail

router = APIRouter(prefix="/calendar-tasks", tags=["Calendar Tasks"])

_WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _assert_client_access(current_user, client_id: str, db: Session) -> None:
    """If the caller is a pure client (role 6), verify they only access their own data."""
    roles = _user_role_ids(current_user.id, db)
    if CLIENT in roles and not roles.intersection({SUPERADMIN, ADMIN, COACH}):
        own = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
        if not own or own.id != client_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Sin acceso")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _monday(d: date) -> date:
    """Return the Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


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


def _build_series(data, coach_user_id: int) -> list:
    """Return a list of CalendarTask instances for a recurring series."""
    color = data.color or COLOR_MAP.get(data.task_type, "#9CA3AF")
    group_id = int(datetime.utcnow().timestamp() * 1000) % 2147483647
    current = data.task_date
    tasks = []
    while current <= data.recurrence_end_date:
        tasks.append(CalendarTask(
            client_user_detail_id=data.client_user_detail_id,
            coach_user_id=coach_user_id,
            task_date=current,
            task_type=data.task_type,
            title=data.title,
            notes=data.notes,
            color=color,
            done=False,
            recurrence=data.recurrence,
            recurrence_end_date=data.recurrence_end_date,
            recurrence_group_id=group_id,
        ))
        current = _next_date(current, data.recurrence)
    return tasks


# ── Schemas ───────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    client_user_detail_id: str
    task_date: date
    task_type: str
    title: Optional[str] = None
    notes: Optional[str] = None
    color: Optional[str] = None
    recurrence: Optional[str] = "none"        # none / daily / weekly / monthly
    recurrence_end_date: Optional[date] = None


class TaskItem(BaseModel):
    """Single item inside a bulk-create request."""
    task_date: date
    task_type: str
    title: Optional[str] = None
    notes: Optional[str] = None
    color: Optional[str] = None


class BulkCreate(BaseModel):
    client_user_detail_id: str
    tasks: List[TaskItem]


class CopyWeek(BaseModel):
    client_user_detail_id: str
    source_week: date    # any date in the source week
    target_week: date    # any date in the target week
    overwrite: bool = False  # if True, delete existing tasks in target week first


class TaskUpdate(BaseModel):
    task_date: Optional[date] = None
    task_type: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    color: Optional[str] = None
    checkin_id: Optional[str] = None


class DoneToggle(BaseModel):
    done: bool
    checkin_id: Optional[str] = None


class CheckinRegister(BaseModel):
    """Payload for POST /{id}/checkin — creates WeeklyCheckin and marks task done."""
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    waist: Optional[float] = None
    chest: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None


# ── Read endpoints ────────────────────────────────────────────────────────────

@router.get(
    "/client/{client_id}",
    summary="Tareas del cliente",
    description="Lista plana de tareas, filtrable por rango de fechas y tipo.",
)
def list_for_client(
    client_id: str,
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    task_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    _assert_client_access(current_user, client_id, db)
    q = db.query(CalendarTask).filter(CalendarTask.client_user_detail_id == client_id)
    if start:
        q = q.filter(CalendarTask.task_date >= start)
    if end:
        q = q.filter(CalendarTask.task_date <= end)
    if task_type:
        q = q.filter(CalendarTask.task_type == task_type)
    return send_response(
        [_out(t) for t in q.order_by(CalendarTask.task_date, CalendarTask.id).all()],
        "OK",
    )


@router.get(
    "/week/{client_id}",
    summary="Vista semanal del cliente",
    description=(
        "Devuelve las tareas y check-ins de la semana (lun–dom) que contiene "
        "la fecha `week`. Respuesta organizada por día de la semana con "
        "contadores de completado para el indicador visual del calendario."
    ),
)
def week_view(
    client_id: str,
    week: date = Query(..., description="Cualquier fecha de la semana deseada"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    _assert_client_access(current_user, client_id, db)
    mon = _monday(week)
    sun = mon + timedelta(days=6)

    tasks = (
        db.query(CalendarTask)
        .filter(
            CalendarTask.client_user_detail_id == client_id,
            CalendarTask.task_date >= mon,
            CalendarTask.task_date <= sun,
        )
        .order_by(CalendarTask.task_date, CalendarTask.id)
        .all()
    )
    checkins = (
        db.query(WeeklyCheckin)
        .filter(
            WeeklyCheckin.client_user_detail_id == client_id,
            WeeklyCheckin.checkin_date >= mon,
            WeeklyCheckin.checkin_date <= sun,
        )
        .all()
    )

    # Build one slot per weekday (0=Mon … 6=Sun)
    days = []
    for i in range(7):
        d = mon + timedelta(days=i)
        day_tasks = [_out(t) for t in tasks if t.task_date == d]
        day_checkins = [_checkin_out(c) for c in checkins if c.checkin_date == d]
        done_count = sum(1 for t in day_tasks if t["done"])
        days.append({
            "date": d.isoformat(),
            "weekday": _WEEKDAYS[i],
            "tasks": day_tasks,
            "checkins": day_checkins,
            "total": len(day_tasks),
            "done": done_count,
            "pending": len(day_tasks) - done_count,
        })

    return send_response(
        {
            "week_start": mon.isoformat(),
            "week_end": sun.isoformat(),
            "days": days,
            "summary": {
                "total_tasks": sum(d["total"] for d in days),
                "done_tasks": sum(d["done"] for d in days),
                "total_checkins": len(checkins),
            },
        },
        "OK",
    )


@router.get(
    "/month/{client_id}",
    summary="Vista mensual del cliente",
    description=(
        "Devuelve todas las tareas y check-ins del mes indicado (year + month), "
        "agrupados por día del mes para renderizar la cuadrícula del calendario."
    ),
)
def month_view(
    client_id: str,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    _assert_client_access(current_user, client_id, db)
    first = date(year, month, 1)
    last_day = _cal.monthrange(year, month)[1]
    last = date(year, month, last_day)

    tasks = (
        db.query(CalendarTask)
        .filter(
            CalendarTask.client_user_detail_id == client_id,
            CalendarTask.task_date >= first,
            CalendarTask.task_date <= last,
        )
        .order_by(CalendarTask.task_date, CalendarTask.id)
        .all()
    )
    checkins = (
        db.query(WeeklyCheckin)
        .filter(
            WeeklyCheckin.client_user_detail_id == client_id,
            WeeklyCheckin.checkin_date >= first,
            WeeklyCheckin.checkin_date <= last,
        )
        .all()
    )

    by_day: dict = {}
    for t in tasks:
        key = t.task_date.isoformat()
        by_day.setdefault(key, {"tasks": [], "checkins": []})
        by_day[key]["tasks"].append(_out(t))
    for c in checkins:
        key = c.checkin_date.isoformat()
        by_day.setdefault(key, {"tasks": [], "checkins": []})
        by_day[key]["checkins"].append(_checkin_out(c))

    return send_response(
        {
            "year": year,
            "month": month,
            "days_in_month": last_day,
            "by_day": by_day,
            "summary": {
                "total_tasks": len(tasks),
                "done_tasks": sum(1 for t in tasks if t.done),
                "total_checkins": len(checkins),
            },
        },
        "OK",
    )


@router.get(
    "/calendar/{client_id}",
    summary="Vista calendario genérica (por rango)",
    description=(
        "Tareas + check-ins del cliente en un rango arbitrario de fechas, "
        "agrupados por fecha ISO (YYYY-MM-DD). Útil para vistas personalizadas."
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


# ── Write endpoints ───────────────────────────────────────────────────────────

@router.post(
    "/bulk",
    summary="Crear múltiples tareas en un solo call",
    description=(
        "Acepta un array de tareas para el mismo cliente y las inserta en una "
        "transacción. Ideal para planificar toda una semana de golpe."
    ),
)
def bulk_create(
    data: BulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    invalid = [i.task_type for i in data.tasks if i.task_type not in VALID_TASK_TYPES]
    if invalid:
        return send_error(f"Tipos inválidos: {', '.join(set(invalid))}")

    created = []
    for item in data.tasks:
        t = CalendarTask(
            client_user_detail_id=data.client_user_detail_id,
            coach_user_id=current_user.id,
            task_date=item.task_date,
            task_type=item.task_type,
            title=item.title,
            notes=item.notes,
            color=item.color or COLOR_MAP.get(item.task_type, "#9CA3AF"),
            done=False,
            recurrence="none",
        )
        db.add(t)
        created.append(t)

    db.commit()
    for t in created:
        db.refresh(t)

    return send_response(
        {"tasks": [_out(t) for t in created], "count": len(created)},
        f"{len(created)} tareas creadas",
    )


@router.post(
    "/copy-week",
    summary="Copiar semana de tareas",
    description=(
        "Duplica todas las tareas de la semana origen a la semana destino, "
        "desplazando las fechas proporcionalmente (lunes→lunes, martes→martes…). "
        "Con overwrite=true elimina las tareas ya existentes en la semana destino."
    ),
)
def copy_week(
    data: CopyWeek,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    src_mon = _monday(data.source_week)
    tgt_mon = _monday(data.target_week)

    if src_mon == tgt_mon:
        return send_error("La semana origen y destino son la misma")

    src_tasks = (
        db.query(CalendarTask)
        .filter(
            CalendarTask.client_user_detail_id == data.client_user_detail_id,
            CalendarTask.task_date >= src_mon,
            CalendarTask.task_date <= src_mon + timedelta(days=6),
        )
        .all()
    )

    if not src_tasks:
        return send_error("No hay tareas en la semana origen")

    if data.overwrite:
        db.query(CalendarTask).filter(
            CalendarTask.client_user_detail_id == data.client_user_detail_id,
            CalendarTask.task_date >= tgt_mon,
            CalendarTask.task_date <= tgt_mon + timedelta(days=6),
        ).delete()

    delta = tgt_mon - src_mon
    created = []
    for src in src_tasks:
        new_t = CalendarTask(
            client_user_detail_id=src.client_user_detail_id,
            coach_user_id=current_user.id,
            task_date=src.task_date + delta,
            task_type=src.task_type,
            title=src.title,
            notes=src.notes,
            color=src.color,
            done=False,
            recurrence="none",
        )
        db.add(new_t)
        created.append(new_t)

    db.commit()
    for t in created:
        db.refresh(t)

    return send_response(
        {"tasks": [_out(t) for t in created], "count": len(created)},
        f"{len(created)} tareas copiadas a la semana del {tgt_mon.isoformat()}",
    )


@router.post(
    "",
    summary="Crear tarea de calendario",
    description=(
        "Crea una tarea en una fecha específica. "
        "Con recurrence ≠ 'none' y recurrence_end_date genera la serie completa."
    ),
)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    if data.task_type not in VALID_TASK_TYPES:
        return send_error(f"Tipo inválido. Válidos: {', '.join(sorted(VALID_TASK_TYPES))}")

    recurrence = data.recurrence or "none"

    if recurrence != "none" and data.recurrence_end_date and data.recurrence_end_date > data.task_date:
        series = _build_series(data, current_user.id)
        if not series:
            return send_error("No se generaron ocurrencias con ese rango de fechas")
        for t in series:
            db.add(t)
        db.commit()
        db.refresh(series[0])
        return send_response(
            {"first": _out(series[0]), "count": len(series), "group_id": series[0].recurrence_group_id},
            f"{len(series)} tareas creadas",
        )

    t = CalendarTask(
        client_user_detail_id=data.client_user_detail_id,
        coach_user_id=current_user.id,
        task_date=data.task_date,
        task_type=data.task_type,
        title=data.title,
        notes=data.notes,
        color=data.color or COLOR_MAP.get(data.task_type, "#9CA3AF"),
        done=False,
        recurrence="none",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return send_response(_out(t), "Tarea creada")


@router.post(
    "/{id}/checkin",
    summary="Registrar check-in desde tarea de calendario",
    description=(
        "Operación atómica exclusiva para tareas de tipo 'checkin': "
        "crea el registro WeeklyCheckin con los datos recibidos, "
        "marca la tarea como completada y enlaza ambos registros. "
        "Si la tarea ya tenía un check-in vinculado lo devuelve sin crear duplicado."
    ),
)
def register_checkin(
    id: int,
    data: CheckinRegister,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    task = db.query(CalendarTask).filter(CalendarTask.id == id).first()
    if not task:
        return send_error("Tarea no encontrada")
    if task.task_type != "checkin":
        return send_error("Esta tarea no es de tipo 'checkin'")

    # Return existing if already linked
    if task.checkin_id:
        existing = db.query(WeeklyCheckin).filter(WeeklyCheckin.id == task.checkin_id).first()
        if existing:
            return send_response(
                {"task": _out(task), "checkin": _checkin_out(existing)},
                "Este check-in ya estaba registrado",
            )

    # Resolve coach UserDetail for the checkin record
    coach_detail = (
        db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    )

    checkin = WeeklyCheckin(
        id=str(uuid.uuid4()),
        client_user_detail_id=task.client_user_detail_id,
        coach_user_detail_id=coach_detail.id if coach_detail else None,
        checkin_date=task.task_date,
        weight=data.weight,
        body_fat=data.body_fat,
        waist=data.waist,
        chest=data.chest,
        hips=data.hips,
        arms=data.arms,
        legs=data.legs,
        notes=data.notes,
        photo_url=data.photo_url,
    )
    db.add(checkin)
    db.flush()

    task.done = True
    task.done_at = datetime.utcnow()
    task.checkin_id = checkin.id

    db.commit()
    db.refresh(task)
    db.refresh(checkin)

    return send_response(
        {"task": _out(task), "checkin": _checkin_out(checkin)},
        "Check-in registrado",
    )


@router.put(
    "/{id}",
    summary="Actualizar tarea",
    description="Modifica los campos de una tarea existente.",
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
    summary="Marcar tarea completada / pendiente",
    description=(
        "Cambia el estado done de la tarea. "
        "Al completar registra done_at. "
        "Para tareas de tipo 'checkin' usa POST /{id}/checkin en su lugar."
    ),
)
def toggle_done(
    id: int,
    data: DoneToggle,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    t = db.query(CalendarTask).filter(CalendarTask.id == id).first()
    if not t:
        return send_error("Tarea no encontrada")
    _assert_client_access(current_user, t.client_user_detail_id, db)
    t.done = data.done
    t.done_at = datetime.utcnow() if data.done else None
    if data.checkin_id is not None:
        t.checkin_id = data.checkin_id
    db.commit()
    db.refresh(t)
    return send_response(_out(t), "Actualizado")


@router.delete(
    "/group/{group_id}",
    summary="Eliminar serie recurrente completa",
    description="Elimina todas las tareas que comparten el mismo recurrence_group_id.",
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
