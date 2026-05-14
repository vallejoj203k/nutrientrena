from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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


class EventUpdate(BaseModel):
    type_event_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    all_day: Optional[int] = None


class EventOut(BaseModel):
    id: int
    user_id: int
    type_event_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: int

    model_config = {"from_attributes": True}
