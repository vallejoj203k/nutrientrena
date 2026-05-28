from pydantic import BaseModel
from typing import Optional


class TypeFoodCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TypeFoodUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class TypeFoodOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: int

    model_config = {"from_attributes": True}


class GroupFoodCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GroupFoodUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class GroupFoodOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: int

    model_config = {"from_attributes": True}
