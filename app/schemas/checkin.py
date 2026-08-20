from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class CheckinCreate(BaseModel):
    client_user_detail_id: str
    checkin_date: date
    weight: Optional[float] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    photo2: Optional[str] = None
    photo3: Optional[str] = None
    body_fat: Optional[float] = None
    muscle_mass: Optional[float] = None
    waist: Optional[float] = None
    chest: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None
    # Cómo dice el cliente que le ha ido la semana. Las rellena él al cumplir
    # su tarea del calendario, pero el coach también puede anotarlas cuando le
    # registra el check-in a mano (una consulta presencial, una llamada).
    energy: Optional[int] = None
    effort: Optional[int] = None
    hunger: Optional[int] = None
    sleep: Optional[int] = None


class CheckinUpdate(BaseModel):
    checkin_date: Optional[date] = None
    weight: Optional[float] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    photo2: Optional[str] = None
    photo3: Optional[str] = None
    body_fat: Optional[float] = None
    muscle_mass: Optional[float] = None
    waist: Optional[float] = None
    chest: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None
    energy: Optional[int] = None
    effort: Optional[int] = None
    hunger: Optional[int] = None
    sleep: Optional[int] = None


class CheckinCoachUpdate(BaseModel):
    coach_notes: Optional[str] = None
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    waist: Optional[float] = None
    chest: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None


class CheckinOut(BaseModel):
    id: str
    client_user_detail_id: str
    coach_user_detail_id: Optional[str] = None
    checkin_date: date
    weight: Optional[float] = None
    notes: Optional[str] = None
    coach_notes: Optional[str] = None
    photo_url: Optional[str] = None
    photo2: Optional[str] = None
    photo3: Optional[str] = None
    body_fat: Optional[float] = None
    muscle_mass: Optional[float] = None
    waist: Optional[float] = None
    chest: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None
    # Cómo se ha sentido la semana, de 0 a 10. La ficha del cliente ya las
    # pintaba y siempre salían "—" porque no llegaban.
    energy: Optional[int] = None
    effort: Optional[int] = None
    hunger: Optional[int] = None
    sleep: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
