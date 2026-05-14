from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TrainingCreate(BaseModel):
    name: str
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    image: Optional[str] = None
    video_url: Optional[str] = None


class TrainingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    state: Optional[int] = None


class TrainingAssignRequest(BaseModel):
    training_ids: List[int]
    user_id: int


class TrainingOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    muscle_group_id: Optional[int] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    state: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
