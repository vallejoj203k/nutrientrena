from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class CheckinCreate(BaseModel):
    client_user_detail_id: str
    checkin_date: date
    weight: Optional[float] = None
    notes: Optional[str] = None


class CheckinCoachUpdate(BaseModel):
    coach_notes: Optional[str] = None
    weight: Optional[float] = None


class CheckinOut(BaseModel):
    id: str
    client_user_detail_id: str
    coach_user_detail_id: Optional[str] = None
    checkin_date: date
    weight: Optional[float] = None
    notes: Optional[str] = None
    coach_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
