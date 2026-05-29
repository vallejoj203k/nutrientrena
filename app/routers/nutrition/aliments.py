from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import csv
import io

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.nutrition.aliment import Aliment
from app.schemas.nutrition.aliment import AlimentCreate, AlimentUpdate, AlimentOut

router = APIRouter(prefix="/aliments", tags=["Nutrition - Aliments"])


def _get_or_404(db: Session, obj_id: str):
    return db.query(Aliment).filter(Aliment.id == obj_id).first()


def _to_float(v: str) -> Optional[float]:
    try:
        return float(v) if v and v.strip() else None
    except ValueError:
        return None


def _to_int(v: str) -> Optional[int]:
    try:
        return int(v) if v and v.strip() else None
    except ValueError:
        return None


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    items = db.query(Aliment).filter(Aliment.parent_id.is_(None)).all()
    return send_response([AlimentOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    group_food_id: Optional[int] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    q = db.query(Aliment).filter(Aliment.parent_id.is_(None))
    if search:
        q = q.filter(Aliment.name.ilike(f"%{search}%"))
    if group_food_id:
        q = q.filter(Aliment.group_food_id == group_food_id)
    total = q.count()
    items = q.order_by(Aliment.name).offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [AlimentOut.model_validate(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": max(1, (total + per_page - 1) // per_page),
        },
        "OK",
    )


@router.get("/{id}/edit")
def edit(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    return send_response(AlimentOut.model_validate(obj).model_dump(), "OK")


@router.post("")
def create(
    data: AlimentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    obj = Aliment(**data.model_dump(), created_user_id=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(AlimentOut.model_validate(obj).model_dump(), "Alimento creado")


@router.put("/{id}/update")
def updated(
    id: str,
    data: AlimentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    obj.updated_user_id = current_user.id
    db.commit()
    db.refresh(obj)
    return send_response(AlimentOut.model_validate(obj).model_dump(), "Actualizado")


@router.delete("/{id}")
def delete_aliment(
    id: str,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    try:
        db.delete(obj)
        db.commit()
    except Exception:
        db.rollback()
        return send_error("No se puede eliminar: el alimento está en uso en una dieta o receta")
    return send_response(None, "Alimento eliminado")


@router.post("/import")
async def import_aliments(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    col_map = {
        "nombre": "name",          "name": "name",
        "marca": "brand",          "brand": "brand",
        "grupo_id": "group_food_id", "group_food_id": "group_food_id",
        "proteinas": "proteins",   "proteins": "proteins",
        "carbohidratos": "carbohydrates", "carbohydrates": "carbohydrates",
        "grasas": "fats",          "fats": "fats",
        "calorias": "calories",    "calories": "calories",
        "cantidad": "quantity",    "quantity": "quantity",
        "comentarios": "comments", "comments": "comments",
    }

    reader = csv.DictReader(io.StringIO(text))
    created = 0
    errors  = []

    for i, row in enumerate(reader, start=2):
        norm = {
            col_map[k.strip().lower()]: v.strip()
            for k, v in row.items()
            if k and k.strip().lower() in col_map
        }
        name = norm.get("name")
        if not name:
            errors.append(f"Fila {i}: columna 'nombre' requerida")
            continue

        aliment = Aliment(
            name=name,
            brand=norm.get("brand") or None,
            group_food_id=_to_int(norm.get("group_food_id", "")),
            proteins=_to_float(norm.get("proteins", "")),
            carbohydrates=_to_float(norm.get("carbohidratos", "") or norm.get("carbohydrates", "")),
            fats=_to_float(norm.get("fats", "")),
            calories=_to_float(norm.get("calories", "")),
            quantity=_to_float(norm.get("quantity", "")),
            comments=norm.get("comments") or None,
            created_user_id=current_user.id,
        )
        db.add(aliment)
        created += 1

    db.commit()
    suffix = f" ({len(errors)} filas con error)" if errors else ""
    return send_response(
        {"created": created, "errors": errors},
        f"{created} alimentos importados{suffix}",
    )

