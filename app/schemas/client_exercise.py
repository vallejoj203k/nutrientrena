from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ClientExerciseCreate(BaseModel):
    client_id: int
    name: str
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    secondary_muscle_group_id: Optional[int] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    exercise_type: Optional[str] = None  # compound/isolation/cardio/mobility
    location: Optional[str] = None  # gym/home/outdoor/both


class ClientExerciseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    secondary_muscle_group_id: Optional[int] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    exercise_type: Optional[str] = None
    location: Optional[str] = None


class ClientExerciseOut(BaseModel):
    id: int
    client_id: int
    name: str
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    secondary_muscle_group_id: Optional[int] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    exercise_type: Optional[str] = None
    location: Optional[str] = None
    created_user_id: Optional[int] = None
    updated_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
