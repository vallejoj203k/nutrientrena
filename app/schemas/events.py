from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime, date


RECURRENCE_VALUES = Literal["none", "daily", "weekly", "monthly"]


class TypeEventCreate(BaseModel):
    name: str
    color: Optional[str] = None


class TypeEventUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    state: Optional[int] = None


class TypeEventOut(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    state: int

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    user_id: Optional[int] = None
    type_event_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: Optional[int] = 0
    recurrence: Optional[RECURRENCE_VALUES] = "none"
    recurrence_end_date: Optional[date] = None  # required when recurrence != none


class EventUpdate(BaseModel):
    type_event_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    all_day: Optional[int] = None
    recurrence: Optional[RECURRENCE_VALUES] = None
    recurrence_end_date: Optional[date] = None


class EventOut(BaseModel):
    id: int
    user_id: int
    type_event_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: int
    recurrence: Optional[str] = None
    recurrence_end_date: Optional[date] = None
    recurrence_group_id: Optional[int] = None
    type_event: Optional[TypeEventOut] = None

    model_config = {"from_attributes": True}
