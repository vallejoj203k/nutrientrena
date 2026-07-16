from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class WeeklyMenuDayIn(BaseModel):
    day_index: int
    name: Optional[str] = None
    diet_id: Optional[str] = None


class WeeklyMenuDayOut(BaseModel):
    day_index: int
    name: Optional[str] = None
    diet_id: Optional[str] = None
    calories: Optional[float] = None
    diet_title: Optional[str] = None

    model_config = {"from_attributes": True}


class WeeklyMenuCreate(BaseModel):
    name: str
    description: Optional[str] = None
    days: List[WeeklyMenuDayIn] = []


class WeeklyMenuUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = None
    days: Optional[List[WeeklyMenuDayIn]] = None


class WeeklyMenuOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_favorite: bool
    days: List[WeeklyMenuDayOut] = []
    assigned_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
