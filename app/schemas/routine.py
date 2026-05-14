from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RoutineDayDetailCreate(BaseModel):
    training_id: int
    sets: Optional[int] = None
    reps: Optional[str] = None
    weight: Optional[float] = None
    rest_seconds: Optional[int] = None
    notes: Optional[str] = None
    order: Optional[int] = 0


class RoutineDayCreate(BaseModel):
    name: Optional[str] = None
    day_number: Optional[int] = None
    rest: Optional[int] = 0
    details: Optional[List[RoutineDayDetailCreate]] = []


class RoutineCreate(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    weeks: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    days: Optional[List[RoutineDayCreate]] = []


class RoutineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[int] = None
    weeks: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    state: Optional[int] = None
    days: Optional[List[RoutineDayCreate]] = None


class RoutineCloneRequest(BaseModel):
    routine_id: int
    client_id: Optional[int] = None


class RoutineAssignRequest(BaseModel):
    routine_id: int
    client_id: int


class RoutineListRequest(BaseModel):
    ids: List[int]


class BulkCreateClientRequest(BaseModel):
    client_ids: List[int]
    routine_id: int


class RoutineDayDetailOut(BaseModel):
    id: int
    training_id: int
    sets: Optional[int] = None
    reps: Optional[str] = None
    weight: Optional[float] = None
    rest_seconds: Optional[int] = None
    notes: Optional[str] = None
    order: int

    model_config = {"from_attributes": True}


class RoutineDayOut(BaseModel):
    id: int
    name: Optional[str] = None
    day_number: Optional[int] = None
    rest: int
    details: List[RoutineDayDetailOut] = []

    model_config = {"from_attributes": True}


class RoutineOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    instructor_id: Optional[int] = None
    weeks: Optional[int] = None
    state: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    days: List[RoutineDayOut] = []

    model_config = {"from_attributes": True}
