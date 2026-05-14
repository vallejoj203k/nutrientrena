from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreateRequest(BaseModel):
    name: str
    last_name: Optional[str] = None
    email: EmailStr
    password: str
    phone: Optional[str] = None
    document: Optional[str] = None
    birth_date: Optional[datetime] = None
    gender_id: Optional[int] = None
    country_id: Optional[int] = None
    role_id: Optional[int] = None
    instructor_id: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activity_level_id: Optional[int] = None
    training_level_id: Optional[int] = None
    goal_id: Optional[int] = None
    notes: Optional[str] = None


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    document: Optional[str] = None
    birth_date: Optional[datetime] = None
    gender_id: Optional[int] = None
    country_id: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activity_level_id: Optional[int] = None
    training_level_id: Optional[int] = None
    goal_id: Optional[int] = None
    notes: Optional[str] = None


class UserStateRequest(BaseModel):
    state: int


class UserAssignRequest(BaseModel):
    user_id: int
    instructor_id: int


class WeeksTrainingRequest(BaseModel):
    user_id: int
    weeks: int


class UserOut(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = None
    email: str
    slug: Optional[str] = None
    phone: Optional[str] = None
    document: Optional[str] = None
    state: int
    photo: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    role_id: Optional[int] = None
    instructor_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
