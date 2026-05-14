from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.event_user import EventUser
from app.models.type_event import TypeEvent
from app.schemas.events import EventCreate, EventUpdate, EventOut, TypeEventCreate, TypeEventUpdate, TypeEventOut

router_events = APIRouter(prefix="/events", tags=["Events"])
router_type_events = APIRouter(prefix="/type-events", tags=["Type Events"])


def _get_event_or_404(db: Session, event_id: int) -> EventUser:
    obj = db.query(EventUser).filter(EventUser.id == event_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return obj


def _get_type_event_or_404(db: Session, obj_id: int) -> TypeEvent:
    obj = db.query(TypeEvent).filter(TypeEvent.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tipo de evento no encontrado")
    return obj


@router_events.post("")
def create_event(data: EventCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
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
    return EventOut.model_validate(event)


@router_events.get("/search")
def search_events(
    user_id: Optional[int] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(EventUser)
    uid = user_id or current_user.id
    q = q.filter(EventUser.user_id == uid)
    if start:
        q = q.filter(EventUser.start_date >= start)
    if end:
        q = q.filter(EventUser.start_date <= end)
    return [EventOut.model_validate(e) for e in q.all()]


@router_events.delete("/delete/{id}")
def delete_event(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    event = _get_event_or_404(db, id)
    db.delete(event)
    db.commit()
    return {"message": "Evento eliminado"}


@router_events.post("/update/{id}")
def update_event(id: int, data: EventUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    event = _get_event_or_404(db, id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(event, f, v)
    db.commit()
    db.refresh(event)
    return EventOut.model_validate(event)


@router_type_events.post("")
def create_type(data: TypeEventCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = TypeEvent(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return TypeEventOut.model_validate(obj)


@router_type_events.post("/update/{id}")
def update_type(id: int, data: TypeEventUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_type_event_or_404(db, id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return TypeEventOut.model_validate(obj)


@router_type_events.get("/find-all")
def find_all_types(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [TypeEventOut.model_validate(i) for i in db.query(TypeEvent).filter(TypeEvent.state == 1).all()]


@router_type_events.get("/search")
def search_types(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(TypeEvent)
    if search:
        q = q.filter(TypeEvent.name.ilike(f"%{search}%"))
    return [TypeEventOut.model_validate(i) for i in q.all()]


@router_type_events.delete("/delete/{id}")
def delete_type(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_type_event_or_404(db, id)
    db.delete(obj)
    db.commit()
    return {"message": "Tipo de evento eliminado"}
