from pydantic import BaseModel
from typing import Optional, List

# El mismo resumen de alimento que usan las dietas. Se reutiliza a
# propósito: dos versiones del mismo dato acaban diciendo cosas distintas.
from app.schemas.nutrition.diet import AlimentSimpleOut


class RecipeDetailCreate(BaseModel):
    aliment_id: str
    quantity: Optional[float] = None
    unit_id: Optional[int] = None
    notes: Optional[str] = None
    order: Optional[int] = 0


class RecipeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    category_id: Optional[int] = None
    categories: Optional[str] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    image: Optional[str] = None
    meal_type: Optional[str] = None
    details: Optional[List[RecipeDetailCreate]] = []


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    category_id: Optional[int] = None
    categories: Optional[str] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    image: Optional[str] = None
    meal_type: Optional[str] = None
    state: Optional[int] = None
    details: Optional[List[RecipeDetailCreate]] = None


class RecipeAssignRequest(BaseModel):
    recipe_id: int
    client_id: int


class RecipeDetailOut(BaseModel):
    id: int
    aliment_id: str
    # Sin esto la receta solo sabía a QUÉ id apunta cada ingrediente: el panel
    # de detalle ponía "Ingrediente · 200g" en todas las líneas, y el editor
    # tenía que pedir los alimentos uno a uno para recuperar los nombres.
    aliment: Optional[AlimentSimpleOut] = None
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
    categories: Optional[str] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    image: Optional[str] = None
    meal_type: Optional[str] = None
    state: int
    organization_id: Optional[str] = None
    details: List[RecipeDetailOut] = []

    model_config = {"from_attributes": True}
