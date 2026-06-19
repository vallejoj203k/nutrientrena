from pydantic import BaseModel
from typing import Optional


class AlimentDescriptionIn(BaseModel):
    vita: Optional[float] = None
    vitb1: Optional[float] = None
    vitb2: Optional[float] = None
    vitb3: Optional[float] = None
    vitb5: Optional[float] = None
    vitb6: Optional[float] = None
    vitb9: Optional[float] = None
    vitb12: Optional[float] = None
    vitc: Optional[float] = None
    vitd: Optional[float] = None
    vite: Optional[float] = None
    vitk: Optional[float] = None
    calina: Optional[float] = None
    calcium: Optional[float] = None
    copper: Optional[float] = None
    iron: Optional[float] = None
    magnesium: Optional[float] = None
    manganese: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    selenium: Optional[float] = None
    sodium: Optional[float] = None
    zinc: Optional[float] = None
    water: Optional[float] = None
    fiber: Optional[float] = None
    cholesterol: Optional[float] = None
    saturated_fats: Optional[float] = None
    mono_saturated_fats: Optional[float] = None
    poli_saturated_fats: Optional[float] = None
    glycemic_index: Optional[float] = None


class AlimentDescriptionOut(AlimentDescriptionIn):
    id: Optional[int] = None
    model_config = {"from_attributes": True}


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
    description: Optional[AlimentDescriptionIn] = None


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
    description: Optional[AlimentDescriptionIn] = None


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
    description: Optional[AlimentDescriptionOut] = None

    model_config = {"from_attributes": True}
