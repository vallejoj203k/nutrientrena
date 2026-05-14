from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlimentCreate(BaseModel):
    name: str
    type_food_id: Optional[int] = None
    group_food_id: Optional[int] = None
    unit_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    quantity: Optional[float] = None
    description: Optional[str] = None


class AlimentUpdate(BaseModel):
    name: Optional[str] = None
    type_food_id: Optional[int] = None
    group_food_id: Optional[int] = None
    unit_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    quantity: Optional[float] = None
    description: Optional[str] = None
    state: Optional[int] = None


class AlimentOut(BaseModel):
    id: int
    name: str
    type_food_id: Optional[int] = None
    group_food_id: Optional[int] = None
    unit_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    quantity: Optional[float] = None
    state: int

    model_config = {"from_attributes": True}
