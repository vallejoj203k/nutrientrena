from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DietDetailCreate(BaseModel):
    aliment_id: Optional[int] = None
    recipe_id: Optional[int] = None
    meal_type_id: Optional[int] = None
    quantity: Optional[float] = None
    unit_id: Optional[int] = None
    notes: Optional[str] = None
    order: Optional[int] = 0


class DietCreate(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    category_id: Optional[int] = None
    goal_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    weeks: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    details: Optional[List[DietDetailCreate]] = []


class DietUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[int] = None
    category_id: Optional[int] = None
    goal_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    weeks: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    state: Optional[int] = None
    details: Optional[List[DietDetailCreate]] = None


class DietAssignRequest(BaseModel):
    client_id: int


class DietDetailOut(BaseModel):
    id: int
    aliment_id: Optional[int] = None
    recipe_id: Optional[int] = None
    meal_type_id: Optional[int] = None
    quantity: Optional[float] = None
    unit_id: Optional[int] = None
    notes: Optional[str] = None
    order: int

    model_config = {"from_attributes": True}


class DietOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    instructor_id: Optional[int] = None
    category_id: Optional[int] = None
    goal_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    weeks: Optional[int] = None
    state: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    details: List[DietDetailOut] = []

    model_config = {"from_attributes": True}
