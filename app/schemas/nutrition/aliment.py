from pydantic import BaseModel
from typing import Optional


class AlimentCreate(BaseModel):
    group_food_id: Optional[int] = None
    brand: Optional[str] = None
    name: str
    quantity: Optional[float] = None
    quantity_type_id: Optional[int] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    fats: Optional[float] = None
    calories: Optional[float] = None
    comments: Optional[str] = None


class AlimentUpdate(BaseModel):
    group_food_id: Optional[int] = None
    brand: Optional[str] = None
    name: Optional[str] = None
    quantity: Optional[float] = None
    quantity_type_id: Optional[int] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    fats: Optional[float] = None
    calories: Optional[float] = None
    comments: Optional[str] = None
    status: Optional[int] = None


class QuantityTypeOut(BaseModel):
    id: int
    description: str
    model_config = {"from_attributes": True}


class AlimentOut(BaseModel):
    id: str
    group_food_id: Optional[int] = None
    brand: Optional[str] = None
    name: str
    quantity: Optional[float] = None
    quantity_type_id: Optional[int] = None
    quantity_type: Optional[QuantityTypeOut] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    fats: Optional[float] = None
    calories: Optional[float] = None
    comments: Optional[str] = None
    parent_id: Optional[str] = None

    model_config = {"from_attributes": True}
