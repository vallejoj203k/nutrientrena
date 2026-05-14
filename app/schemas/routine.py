from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RoutineDayDetailCreate(BaseModel):
    muscle_group_id: Optional[int] = None
    training_id: Optional[int] = None
    series: Optional[int] = None
    repetitions: Optional[str] = None
    break_time: Optional[int] = None


class RoutineDayCreate(BaseModel):
    day_name: Optional[str] = None
    content_html: Optional[str] = None  # maps to description in DB
    details: Optional[List[RoutineDayDetailCreate]] = []


class RoutineCreate(BaseModel):
    name: str
    gender_id: Optional[int] = None
    training: Optional[str] = None
    training_level_id: Optional[int] = None
    time: Optional[int] = None
    days: Optional[int] = None
    days_list: Optional[List[RoutineDayCreate]] = []


class RoutineUpdate(BaseModel):
    name: Optional[str] = None
    gender_id: Optional[int] = None
    training: Optional[str] = None
    training_level_id: Optional[int] = None
    time: Optional[int] = None
    days: Optional[int] = None
    days_list: Optional[List[RoutineDayCreate]] = None


class RoutineCloneRequest(BaseModel):
    id: int


class RoutineAssignRequest(BaseModel):
    name: str
    client_id: str  # UserDetail UUID
    gender_id: Optional[int] = None
    training: Optional[str] = None
    training_level_id: Optional[int] = None
    time: Optional[int] = None
    days: Optional[int] = None
    days_list: Optional[List[RoutineDayCreate]] = []


class RoutineListRequest(BaseModel):
    ids: List[int]


class RoutineBulkDetailCreate(BaseModel):
    id: Optional[int] = None
    name: str
    gender_id: Optional[int] = None
    training: Optional[str] = None
    training_level_id: Optional[int] = None
    time: Optional[int] = None
    days: Optional[int] = None
    days_list: Optional[List[RoutineDayCreate]] = []


class BulkCreateClientRequest(BaseModel):
    client_id: str  # UserDetail UUID
    routines: List[RoutineBulkDetailCreate]


class TrainingOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class MuscleGroupOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class RoutineDayDetailOut(BaseModel):
    id: int
    routine_id: int
    routine_day_id: int
    muscle_group_id: Optional[int] = None
    muscle_group: Optional[MuscleGroupOut] = None
    training_id: Optional[int] = None
    training: Optional[TrainingOut] = None
    series: Optional[int] = None
    repetitions: Optional[str] = None
    break_time: Optional[int] = None

    model_config = {"from_attributes": True}


class RoutineDayOut(BaseModel):
    id: int
    day_name: Optional[str] = None
    content_html: Optional[str] = None  # alias for description
    details: List[RoutineDayDetailOut] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_day(cls, day):
        return cls(
            id=day.id,
            day_name=day.day_name,
            content_html=day.description,
            details=[RoutineDayDetailOut.model_validate(d) for d in day.details],
        )


class RoutineOut(BaseModel):
    id: int
    name: str
    user_id: Optional[int] = None
    gender_id: Optional[int] = None
    training: Optional[str] = None
    training_level_id: Optional[int] = None
    time: Optional[int] = None
    days: Optional[int] = None
    created_at: Optional[datetime] = None
    days_list: List[RoutineDayOut] = []

    model_config = {"from_attributes": True}
