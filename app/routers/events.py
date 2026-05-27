from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.event_user import EventUser
from app.models.type_event import TypeEvent
from app.schemas.events import EventCreate, EventUpdate, EventOut, TypeEventCreate, TypeEventUpdate, TypeEventOut

router_events = APIRouter(prefix="/events", tags=["Events"])
router_type_events = APIRouter(prefix="/type-events", tags=["Type Events"])


def _get_event_or_404(db: Session, event_id: int):
    return db.query(EventUser).filter(EventUser.id == event_id).first()


def _get_type_or_404(db: Session, obj_id: int):
    return db.query(TypeEvent).filter(TypeEvent.id == obj_id).first()


@router_events.post("")
def create_event(data: EventCreate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    event = EventUser(
        user_id=data.user_id or current_user.id,
        type_event_id=data.type_event_id,
        title=data.title,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        all_day=data.all_day or 0,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return send_response(EventOut.model_validate(event).model_dump(), "Evento creado")


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
    return send_response([EventOut.model_validate(e).model_dump() for e in q.all()], "OK")


@router_events.delete("/delete/{id}")
def delete_event(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    event = _get_event_or_404(db, id)
    if not event:
        return send_error("Evento no encontrado")
    db.delete(event)
    db.commit()
    return send_response(None, "Evento eliminado")


@router_events.post("/update/{id}")
def update_event(id: int, data: EventUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    event = _get_event_or_404(db, id)
    if not event:
        return send_error("Evento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(event, f, v)
    db.commit()
    db.refresh(event)
    return send_response(EventOut.model_validate(event).model_dump(), "Evento actualizado")


@router_type_events.post("")
def create_type(data: TypeEventCreate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = TypeEvent(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(TypeEventOut.model_validate(obj).model_dump(), "Tipo de evento creado")


@router_type_events.post("/update/{id}")
def update_type(id: int, data: TypeEventUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_type_or_404(db, id)
    if not obj:
        return send_error("Tipo de evento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(TypeEventOut.model_validate(obj).model_dump(), "Actualizado")


@router_type_events.get("/find-all")
def find_all_types(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
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
def delete_type(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_type_or_404(db, id)
    if not obj:
        return send_error("Tipo de evento no encontrado")
    db.delete(obj)
    db.commit()
    return send_response(None, "Tipo de evento eliminado")
