import calendar
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.event_user import EventUser
from app.models.type_event import TypeEvent
from app.schemas.events import EventCreate, EventUpdate, EventOut, TypeEventCreate, TypeEventUpdate, TypeEventOut

router_events = APIRouter(prefix="/events", tags=["Events"])
router_type_events = APIRouter(prefix="/type-events", tags=["Type Events"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _out(event: EventUser) -> dict:
    return EventOut.model_validate(event).model_dump()


def _add_months(dt: datetime, months: int) -> datetime:
    """Advance datetime by N months without external deps."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _next_occurrence(dt: datetime, recurrence: str) -> datetime:
    if recurrence == "daily":
        return dt + timedelta(days=1)
    if recurrence == "weekly":
        return dt + timedelta(weeks=1)
    if recurrence == "monthly":
        return _add_months(dt, 1)
    return dt


def _generate_occurrences(data: EventCreate, user_id: int, group_id: int) -> list[EventUser]:
    """Return all EventUser instances for a recurring series."""
    events = []
    duration = (data.end_date - data.start_date) if data.end_date else None
    current = data.start_date
    while current.date() <= data.recurrence_end_date:
        e = EventUser(
            user_id=user_id,
            type_event_id=data.type_event_id,
            title=data.title,
            description=data.description,
            start_date=current,
            end_date=(current + duration) if duration else None,
            all_day=data.all_day or 0,
            recurrence=data.recurrence,
            recurrence_end_date=data.recurrence_end_date,
            recurrence_group_id=group_id,
        )
        events.append(e)
        current = _next_occurrence(current, data.recurrence)
    return events


# ── Events ────────────────────────────────────────────────────────────────────

@router_events.post("")
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    uid = data.user_id or current_user.id

    if data.recurrence and data.recurrence != "none" and data.recurrence_end_date:
        # Generate a unique group_id using timestamp
        group_id = int(datetime.utcnow().timestamp() * 1000) % 2147483647
        instances = _generate_occurrences(data, uid, group_id)
        if not instances:
            return send_error("La fecha de fin de recurrencia debe ser posterior al inicio")
        for e in instances:
            db.add(e)
        db.commit()
        # Return the first occurrence as representative
        db.refresh(instances[0])
        return send_response(
            {"first": _out(instances[0]), "count": len(instances), "group_id": group_id},
            f"{len(instances)} eventos recurrentes creados",
        )

    # Single event
    event = EventUser(
        user_id=uid,
        type_event_id=data.type_event_id,
        title=data.title,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        all_day=data.all_day or 0,
        recurrence=data.recurrence or "none",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return send_response(_out(event), "Evento creado")


@router_events.get("/search")
def search_events(
    user_id: Optional[int] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    uid = user_id or current_user.id
    q = db.query(EventUser).filter(EventUser.user_id == uid)
    if start:
        q = q.filter(EventUser.start_date >= start)
    if end:
        q = q.filter(EventUser.start_date <= end)
    q = q.order_by(EventUser.start_date)
    return send_response([_out(e) for e in q.all()], "OK")


@router_events.post("/update/{id}")
def update_event(
    id: int,
    data: EventUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    event = db.query(EventUser).filter(EventUser.id == id).first()
    if not event:
        return send_error("Evento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(event, f, v)
    db.commit()
    db.refresh(event)
    return send_response(_out(event), "Evento actualizado")


@router_events.delete("/delete/{id}")
def delete_event(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    event = db.query(EventUser).filter(EventUser.id == id).first()
    if not event:
        return send_error("Evento no encontrado")
    db.delete(event)
    db.commit()
    return send_response(None, "Evento eliminado")


@router_events.delete("/delete-group/{group_id}")
def delete_event_group(
    group_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    """Delete all events belonging to a recurrence group."""
    deleted = db.query(EventUser).filter(EventUser.recurrence_group_id == group_id).delete()
    db.commit()
    return send_response({"deleted": deleted}, f"{deleted} eventos eliminados")


# ── Type Events ───────────────────────────────────────────────────────────────

@router_type_events.post("")
def create_type(
    data: TypeEventCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    obj = TypeEvent(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(TypeEventOut.model_validate(obj).model_dump(), "Tipo de evento creado")


@router_type_events.post("/update/{id}")
def update_type(
    id: int,
    data: TypeEventUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    obj = db.query(TypeEvent).filter(TypeEvent.id == id).first()
    if not obj:
        return send_error("Tipo de evento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(TypeEventOut.model_validate(obj).model_dump(), "Actualizado")


@router_type_events.get("/find-all")
def find_all_types(
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    items = db.query(TypeEvent).filter(TypeEvent.state == 1).all()
    return send_response([TypeEventOut.model_validate(i).model_dump() for i in items], "OK")


@router_type_events.get("/search")
def search_types(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(TypeEvent)
    if search:
        q = q.filter(TypeEvent.name.ilike(f"%{search}%"))
    return send_response([TypeEventOut.model_validate(i).model_dump() for i in q.all()], "OK")


@router_type_events.delete("/delete/{id}")
def delete_type(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    obj = db.query(TypeEvent).filter(TypeEvent.id == id).first()
    if not obj:
        return send_error("Tipo de evento no encontrado")
    db.delete(obj)
    db.commit()
    return send_response(None, "Tipo de evento eliminado")
