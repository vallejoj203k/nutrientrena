from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TrainingCreate(BaseModel):
    name: str
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    secondary_muscle_group_id: Optional[int] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    exercise_type: Optional[str] = None  # compound/isolation/cardio/mobility
    location: Optional[str] = None  # gym/home/outdoor/both


class TrainingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    secondary_muscle_group_id: Optional[int] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    exercise_type: Optional[str] = None
    location: Optional[str] = None
    state: Optional[int] = None


class TrainingAssignRequest(BaseModel):
    training_ids: List[int]
    user_id: int


class TrainingOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    muscle_group_name: Optional[str] = None
    secondary_muscle_group_id: Optional[int] = None
    secondary_muscle_group_name: Optional[str] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    exercise_type: Optional[str] = None
    location: Optional[str] = None
    state: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_training(cls, t):
        return cls(
            id=t.id,
            name=t.name,
            description=t.description,
            muscle_group_id=t.muscle_group_id,
            muscle_group_name=t.muscle_group.name if t.muscle_group else None,
            secondary_muscle_group_id=t.secondary_muscle_group_id,
            secondary_muscle_group_name=t.secondary_muscle_group.name if t.secondary_muscle_group else None,
            image=t.image,
            video_url=t.video_url,
            exercise_type=t.exercise_type,
            location=t.location,
            state=t.state,
            created_at=t.created_at,
        )
