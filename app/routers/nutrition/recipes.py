from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.nutrition.recipe import Recipe, RecipeDetail
from app.schemas.nutrition.recipe import RecipeCreate, RecipeUpdate, RecipeOut, RecipeAssignRequest

router = APIRouter(prefix="/recipes", tags=["Nutrition - Recipes"])


def _get_or_404(db: Session, recipe_id: int):
    return db.query(Recipe).filter(Recipe.id == recipe_id).first()


@router.get("/findAll", summary="Listar recetas", description="Retorna todas las recetas activas del catálogo.")
def find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    items = db.query(Recipe).filter(Recipe.state == 1).all()
    return send_response([RecipeOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search", summary="Buscar recetas", description="Búsqueda paginada de recetas por nombre.")
def search(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    q = db.query(Recipe).filter(Recipe.state == 1)
    if search:
        q = q.filter(Recipe.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(Recipe.name).offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [RecipeOut.model_validate(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": max(1, (total + per_page - 1) // per_page),
        },
        "OK",
    )


@router.post("/assign", summary="Asignar receta a usuario", description="Asigna una receta del catálogo a un usuario.")
def assign(data: RecipeAssignRequest, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    if not _get_or_404(db, data.recipe_id):
        return send_error("Receta no encontrada")
    return send_response(None, "Receta asignada")


@router.get("/client/{client_id}", summary="Recetas del cliente", description="Retorna las recetas asignadas a un cliente específico.")
def clients(client_id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    from app.models.user import UserDetail
    client_detail = db.query(UserDetail).filter(UserDetail.id == client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")
    items = db.query(Recipe).filter(Recipe.instructor_id == client_detail.user_id).all()
    return send_response([RecipeOut.model_validate(i).model_dump() for i in items], "OK")


@router.post("", summary="Crear receta", description="Crea una nueva receta con su lista de ingredientes.")
def create(data: RecipeCreate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    recipe_data = data.model_dump(exclude={"details"})
    recipe_data["instructor_id"] = current_user.id
    recipe = Recipe(**recipe_data)
    db.add(recipe)
    db.flush()
    for detail in (data.details or []):
        db.add(RecipeDetail(recipe_id=recipe.id, **detail.model_dump()))
    db.commit()
    db.refresh(recipe)
    return send_response(RecipeOut.model_validate(recipe).model_dump(), "Receta creada")


@router.get("/{id}/edit", summary="Ver receta", description="Retorna el detalle completo de una receta con sus ingredientes.")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    recipe = _get_or_404(db, id)
    if not recipe:
        return send_error("Receta no encontrada")
    return send_response(RecipeOut.model_validate(recipe).model_dump(), "OK")


@router.delete("/{id}", summary="Eliminar receta", description="Desactiva una receta (soft delete).")
def delete(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    recipe = _get_or_404(db, id)
    if not recipe:
        return send_error("Receta no encontrada")
    recipe.state = 0
    db.commit()
    return send_response(None, "Receta eliminada")


@router.put("/{id}/update", summary="Actualizar receta", description="Modifica una receta y reemplaza su lista de ingredientes.")
def updated(id: int, data: RecipeUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    recipe = _get_or_404(db, id)
    if not recipe:
        return send_error("Receta no encontrada")
    for f, v in data.model_dump(exclude_unset=True, exclude={"details"}).items():
        setattr(recipe, f, v)
    if data.details is not None:
        db.query(RecipeDetail).filter(RecipeDetail.recipe_id == recipe.id).delete()
        for detail in data.details:
            db.add(RecipeDetail(recipe_id=recipe.id, **detail.model_dump()))
    db.commit()
    db.refresh(recipe)
    return send_response(RecipeOut.model_validate(recipe).model_dump(), "Receta actualizada")
