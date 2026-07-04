from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.nutrition.aliment import QuantityTypeOut


class DietFoodAlimentCreate(BaseModel):
    id: Optional[int] = None
    aliment_id: str
    quantity_calc: Optional[float] = None
    order: Optional[int] = 0
    delete: Optional[bool] = False


class DietFoodCreate(BaseModel):
    id: Optional[int] = None
    name: str
    time: Optional[str] = None
    detail: Optional[List[DietFoodAlimentCreate]] = []
    delete: Optional[bool] = False


class DietCreate(BaseModel):
    title: str
    calories: Optional[float] = None
    quantity: Optional[float] = None
    type_id: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    level_activity_id: Optional[int] = None
    objective_id: Optional[int] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    deficit: Optional[float] = None
    surplus: Optional[float] = None
    foods: Optional[List[DietFoodCreate]] = []
    pathology_ids: Optional[List[int]] = []
    notes: Optional[str] = None


class DietUpdate(DietCreate):
    id: str
    title: Optional[str] = None


class AlimentSimpleOut(BaseModel):
    id: str
    name: str
    group_food_id: Optional[int] = None
    quantity: Optional[float] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbohydrates: Optional[float] = None
    fats: Optional[float] = None
    quantity_type: Optional[QuantityTypeOut] = None
    quantity_unit: Optional[str] = None
    model_config = {"from_attributes": True}


class DietFoodAlimentOut(BaseModel):
    id: int
    aliment_id: str
    aliment: Optional[AlimentSimpleOut] = None
    quantity: Optional[float] = None
    order: int
    model_config = {"from_attributes": True}


class DietFoodOut(BaseModel):
    id: int
    name: str
    time: Optional[str] = None
    detail: List[DietFoodAlimentOut] = []
    model_config = {"from_attributes": True}


class DietDetailOut(BaseModel):
    id: int
    height: Optional[float] = None
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    level_activity_id: Optional[int] = None
    objective_id: Optional[int] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    deficit: Optional[float] = None
    surplus: Optional[float] = None
    model_config = {"from_attributes": True}


class PathologyOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class DietOut(BaseModel):
    id: str
    title: str
    calories: Optional[float] = None
    quantity: Optional[float] = None
    type_id: Optional[int] = None
    user_id: Optional[int] = None
    organization_id: Optional[str] = None
    created_at: Optional[datetime] = None
    detail: Optional[DietDetailOut] = None
    foods: List[DietFoodOut] = []
    pathologies: List[PathologyOut] = []
    notes: Optional[str] = None
    model_config = {"from_attributes": True}
