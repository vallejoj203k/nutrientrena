from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MuscleGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None


class MuscleGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    state: Optional[int] = None


class MuscleGroupOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    state: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
