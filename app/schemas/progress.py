from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ProgressCreate(BaseModel):
    user_id: Optional[int] = None
    date: date
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    muscle_mass: Optional[float] = None
    waist: Optional[float] = None
    hip: Optional[float] = None
    chest: Optional[float] = None
    arm: Optional[float] = None
    thigh: Optional[float] = None
    notes: Optional[str] = None
    photo: Optional[str] = None
    photo2: Optional[str] = None
    photo3: Optional[str] = None


class ProgressOut(BaseModel):
    id: int
    user_id: int
    date: date
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    muscle_mass: Optional[float] = None
    waist: Optional[float] = None
    hip: Optional[float] = None
    chest: Optional[float] = None
    arm: Optional[float] = None
    thigh: Optional[float] = None
    notes: Optional[str] = None
    photo: Optional[str] = None
    photo2: Optional[str] = None
    photo3: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ClientTargetCreate(BaseModel):
    user_id: Optional[int] = None
    target_weight: Optional[float] = None
    target_body_fat: Optional[float] = None
    target_muscle_mass: Optional[float] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    deficit: Optional[float] = None
    surplus: Optional[float] = None
    protein_ratio: Optional[float] = None
    fat_ratio: Optional[float] = None
    meal_count: Optional[int] = None
    notes: Optional[str] = None


class ClientTargetOut(BaseModel):
    id: int
    user_id: int
    target_weight: Optional[float] = None
    target_body_fat: Optional[float] = None
    target_muscle_mass: Optional[float] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    deficit: Optional[float] = None
    surplus: Optional[float] = None
    protein_ratio: Optional[float] = None
    fat_ratio: Optional[float] = None
    meal_count: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}
