from pydantic import BaseModel
from typing import Optional


class ClientAlimentCreate(BaseModel):
    client_id: int
    group_food_id: Optional[int] = None
    brand: Optional[str] = None
    name: str
    quantity: Optional[float] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    fats: Optional[float] = None
    calories: Optional[float] = None
    comments: Optional[str] = None


class ClientAlimentUpdate(BaseModel):
    group_food_id: Optional[int] = None
    brand: Optional[str] = None
    name: Optional[str] = None
    quantity: Optional[float] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    fats: Optional[float] = None
    calories: Optional[float] = None
    comments: Optional[str] = None


class ClientAlimentOut(BaseModel):
    id: str
    client_id: int
    group_food_id: Optional[int] = None
    brand: Optional[str] = None
    name: str
    quantity: Optional[float] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    fats: Optional[float] = None
    calories: Optional[float] = None
    comments: Optional[str] = None

    model_config = {"from_attributes": True}
