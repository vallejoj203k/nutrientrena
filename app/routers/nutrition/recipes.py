from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.nutrition.recipe import Recipe, RecipeDetail
from app.models.nutrition.diet import DietDetail
from app.schemas.nutrition.recipe import RecipeCreate, RecipeUpdate, RecipeOut, RecipeAssignRequest

router = APIRouter(prefix="/recipes", tags=["Nutrition - Recipes"])


def _get_or_404(db: Session, recipe_id: int) -> Recipe:
    obj = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return obj


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [RecipeOut.model_validate(i) for i in db.query(Recipe).filter(Recipe.state == 1).all()]


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Recipe)
    if search:
        q = q.filter(Recipe.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {"data": [RecipeOut.model_validate(i) for i in items], "total": total, "page": page, "per_page": per_page, "last_page": (total + per_page - 1) // per_page}


@router.post("/assign")
def assign(data: RecipeAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    _get_or_404(db, data.recipe_id)
    db.add(DietDetail(recipe_id=data.recipe_id, diet_id=0))
    db.commit()
    return {"message": "Receta asignada"}


@router.get("/client/{client_id}")
def clients(client_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    diet_details = db.query(DietDetail).filter(DietDetail.recipe_id.isnot(None)).all()
    recipe_ids = list({d.recipe_id for d in diet_details})
    items = db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
    return [RecipeOut.model_validate(i) for i in items]


@router.post("")
def create(data: RecipeCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    recipe_data = data.model_dump(exclude={"details"})
    recipe_data["instructor_id"] = current_user.id
    recipe = Recipe(**recipe_data)
    db.add(recipe)
    db.flush()
    for detail in (data.details or []):
        db.add(RecipeDetail(recipe_id=recipe.id, **detail.model_dump()))
    db.commit()
    db.refresh(recipe)
    return RecipeOut.model_validate(recipe)


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return RecipeOut.model_validate(_get_or_404(db, id))


@router.put("/{id}/update")
def updated(id: int, data: RecipeUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    recipe = _get_or_404(db, id)
    update_data = data.model_dump(exclude_unset=True, exclude={"details"})
    for f, v in update_data.items():
        setattr(recipe, f, v)
    if data.details is not None:
        db.query(RecipeDetail).filter(RecipeDetail.recipe_id == recipe.id).delete()
        for detail in data.details:
            db.add(RecipeDetail(recipe_id=recipe.id, **detail.model_dump()))
    db.commit()
    db.refresh(recipe)
    return RecipeOut.model_validate(recipe)
