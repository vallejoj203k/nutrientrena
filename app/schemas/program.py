from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PhaseIn(BaseModel):
    name: str
    weeks: int
    order: int = 0


class PhaseOut(BaseModel):
    id: int
    name: str
    weeks: int
    order: int

    model_config = {"from_attributes": True}


class ClientMini(BaseModel):
    id: int
    name: str
    email: str
    initials: str

    model_config = {"from_attributes": True}


class ProgramCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    checkins_count: int = 0
    phases: List[PhaseIn] = []


class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    checkins_count: Optional[int] = None
    phases: Optional[List[PhaseIn]] = None


class ProgramAssignRequest(BaseModel):
    client_ids: List[int]


class ProgramOut(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str] = None
    status: str
    checkins_count: int
    coach_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    phases: List[PhaseOut] = []
    clients: List[ClientMini] = []
    total_weeks: int = 0

    model_config = {"from_attributes": True}
