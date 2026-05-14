from pydantic import BaseModel
from typing import Optional, List


class RecipeDetailCreate(BaseModel):
    aliment_id: int
    quantity: Optional[float] = None
    unit_id: Optional[int] = None
    notes: Optional[str] = None
    order: Optional[int] = 0


class RecipeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    category_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    image: Optional[str] = None
    details: Optional[List[RecipeDetailCreate]] = []


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    category_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    image: Optional[str] = None
    state: Optional[int] = None
    details: Optional[List[RecipeDetailCreate]] = None


class RecipeAssignRequest(BaseModel):
    recipe_id: int
    client_id: int


class RecipeDetailOut(BaseModel):
    id: int
    aliment_id: int
    quantity: Optional[float] = None
    unit_id: Optional[int] = None
    notes: Optional[str] = None
    order: int

    model_config = {"from_attributes": True}


class RecipeOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    category_id: Optional[int] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    image: Optional[str] = None
    state: int
    details: List[RecipeDetailOut] = []

    model_config = {"from_attributes": True}
