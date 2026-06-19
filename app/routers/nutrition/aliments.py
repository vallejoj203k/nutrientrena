from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import csv
import io

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response, send_error
from app.models.nutrition.aliment import Aliment, AlimentDescription
from app.schemas.nutrition.aliment import AlimentCreate, AlimentUpdate, AlimentOut
from app.config import settings
from app.services import usda as usda_svc

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


def _usda_query(name: str) -> str:
    """Simplify a long translated food name into a short English-safe USDA query."""
    # Take the first segment before a comma (the main food type)
    short = name.split(",")[0].strip()
    # Strip characters that break USDA URL parsing
    for ch in ['«', '»', '"', "'", '/', '\\', '(', ')', '%']:
        short = short.replace(ch, ' ')
    # Collapse multiple spaces and truncate
    short = ' '.join(short.split())[:80]
    return short or name[:80]


def _upsert_description(db: Session, aliment_id: str, desc_data: dict):
    """Create or update the AlimentDescription row for a given aliment."""
    existing = db.query(AlimentDescription).filter(AlimentDescription.aliment_id == aliment_id).first()
    if existing:
        for field, value in desc_data.items():
            setattr(existing, field, value)
    else:
        db.add(AlimentDescription(aliment_id=aliment_id, **desc_data))


@router.get("/findAll", summary="Listar alimentos", description="Retorna todos los alimentos del catálogo (sin clones).")
def find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    items = db.query(Aliment).filter(Aliment.parent_id.is_(None)).all()
    return send_response([AlimentOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search", summary="Buscar alimentos", description="Búsqueda paginada de alimentos por nombre o grupo de alimentos.")
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


@router.get("/{id}/edit", summary="Ver alimento", description="Retorna el detalle completo de un alimento incluyendo micronutrientes.")
def edit(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    return send_response(AlimentOut.model_validate(obj).model_dump(), "OK")


@router.post("", summary="Crear alimento", description="Agrega un nuevo alimento al catálogo con sus macros y micronutrientes.")
def create(
    data: AlimentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    payload = data.model_dump(exclude={"description"})
    obj = Aliment(**payload, created_user_id=current_user.id)
    db.add(obj)
    db.flush()

    if data.description:
        desc_data = data.description.model_dump(exclude_none=True)
        if desc_data:
            _upsert_description(db, obj.id, desc_data)

    db.commit()
    db.refresh(obj)
    return send_response(AlimentOut.model_validate(obj).model_dump(), "Alimento creado")


@router.put("/{id}/update", summary="Actualizar alimento", description="Modifica los datos nutricionales y micronutrientes de un alimento existente.")
def updated(
    id: str,
    data: AlimentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")

    for f, v in data.model_dump(exclude_unset=True, exclude={"description"}).items():
        setattr(obj, f, v)
    obj.updated_user_id = current_user.id

    if data.description is not None:
        desc_data = data.description.model_dump(exclude_unset=True)
        if desc_data:
            _upsert_description(db, obj.id, desc_data)

    db.commit()
    db.refresh(obj)
    return send_response(AlimentOut.model_validate(obj).model_dump(), "Actualizado")


@router.delete("/{id}", summary="Eliminar alimento", description="Elimina un alimento del catálogo. Falla si está en uso en alguna dieta o receta.")
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


@router.post("/import", summary="Importar alimentos desde CSV", description="Importa alimentos masivamente desde un archivo CSV.")
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
        # micronutrients
        "fibra": "fiber",           "fiber": "fiber",
        "sodio": "sodium",          "sodium": "sodium",
        "calcio": "calcium",        "calcium": "calcium",
        "hierro": "iron",           "iron": "iron",
        "potasio": "potassium",     "potassium": "potassium",
        "magnesio": "magnesium",    "magnesium": "magnesium",
        "fosforo": "phosphorus",    "phosphorus": "phosphorus",
        "zinc": "zinc",
        "selenio": "selenium",      "selenium": "selenium",
        "cobre": "copper",          "copper": "copper",
        "manganeso": "manganese",   "manganese": "manganese",
        "colesterol": "cholesterol", "cholesterol": "cholesterol",
        "grasas_saturadas": "saturated_fats",     "saturated_fats": "saturated_fats",
        "grasas_monoinsaturadas": "mono_saturated_fats", "mono_saturated_fats": "mono_saturated_fats",
        "grasas_poliinsaturadas": "poli_saturated_fats", "poli_saturated_fats": "poli_saturated_fats",
        "agua": "water",            "water": "water",
        "indice_glucemico": "glycemic_index", "glycemic_index": "glycemic_index",
        "vita": "vita",   "vitamina_a": "vita",
        "vitb1": "vitb1", "vitamina_b1": "vitb1",
        "vitb2": "vitb2", "vitamina_b2": "vitb2",
        "vitb3": "vitb3", "vitamina_b3": "vitb3",
        "vitb5": "vitb5", "vitamina_b5": "vitb5",
        "vitb6": "vitb6", "vitamina_b6": "vitb6",
        "vitb9": "vitb9", "vitamina_b9": "vitb9",   "acido_folico": "vitb9",
        "vitb12": "vitb12", "vitamina_b12": "vitb12",
        "vitc": "vitc",   "vitamina_c": "vitc",
        "vitd": "vitd",   "vitamina_d": "vitd",
        "vite": "vite",   "vitamina_e": "vite",
        "vitk": "vitk",   "vitamina_k": "vitk",
    }

    DESC_FIELDS = {
        "vita", "vitb1", "vitb2", "vitb3", "vitb5", "vitb6", "vitb9", "vitb12",
        "vitc", "vitd", "vite", "vitk",
        "calina", "calcium", "copper", "iron", "magnesium", "manganese",
        "phosphorus", "potassium", "selenium", "sodium", "zinc",
        "water", "fiber", "cholesterol", "saturated_fats",
        "mono_saturated_fats", "poli_saturated_fats", "glycemic_index",
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
            carbohydrates=_to_float(norm.get("carbohydrates", "")),
            fats=_to_float(norm.get("fats", "")),
            calories=_to_float(norm.get("calories", "")),
            quantity=_to_float(norm.get("quantity", "")),
            comments=norm.get("comments") or None,
            created_user_id=current_user.id,
        )
        db.add(aliment)
        db.flush()

        desc_data = {f: _to_float(norm.get(f, "")) for f in DESC_FIELDS if norm.get(f)}
        if desc_data:
            db.add(AlimentDescription(aliment_id=aliment.id, **desc_data))

        created += 1

    db.commit()
    suffix = f" ({len(errors)} filas con error)" if errors else ""
    return send_response(
        {"created": created, "errors": errors},
        f"{created} alimentos importados{suffix}",
    )


class UsdaSyncRequest(BaseModel):
    ids: Optional[List[str]] = None
    batch: int = 30  # max aliments per request to avoid gateway timeout


@router.post("/usda-sync", summary="Sincronizar micronutrientes con USDA", description="Busca cada alimento en USDA FoodData Central por nombre y rellena sus micronutrientes.")
async def usda_sync(
    body: UsdaSyncRequest,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    api_key = settings.USDA_API_KEY
    if not api_key:
        return send_error("USDA_API_KEY no configurada en el servidor")

    if body.ids:
        aliments = db.query(Aliment).filter(Aliment.id.in_(body.ids)).all()
    else:
        # sync only those without a description row yet
        synced_ids = db.query(AlimentDescription.aliment_id).scalar_subquery()
        aliments = db.query(Aliment).filter(
            Aliment.parent_id.is_(None),
            ~Aliment.id.in_(synced_ids),
        ).limit(body.batch).all()

    total_pending = db.query(Aliment).filter(
        Aliment.parent_id.is_(None),
        ~Aliment.id.in_(db.query(AlimentDescription.aliment_id).scalar_subquery()),
    ).count() if not body.ids else 0

    synced: List[str] = []
    not_found: List[str] = []
    errors: List[str] = []

    for aliment in aliments:
        try:
            query = _usda_query(aliment.name)
            food = await usda_svc.search_food(api_key, query)
            if not food:
                not_found.append(aliment.name)
                await asyncio.sleep(0.25)
                continue

            micros = usda_svc.extract_micros(food)
            macros = usda_svc.extract_macros(food)

            if aliment.proteins is None and macros.get("proteins") is not None:
                aliment.proteins = macros["proteins"]
            if aliment.carbohydrates is None and macros.get("carbohydrates") is not None:
                aliment.carbohydrates = macros["carbohydrates"]
            if aliment.fats is None and macros.get("fats") is not None:
                aliment.fats = macros["fats"]
            if aliment.calories is None and macros.get("calories") is not None:
                aliment.calories = macros["calories"]

            non_null_micros = {k: v for k, v in micros.items() if v is not None}
            if non_null_micros:
                _upsert_description(db, aliment.id, non_null_micros)

            synced.append(aliment.name)
            await asyncio.sleep(0.25)

        except Exception as e:
            errors.append(f"{aliment.name}: {str(e)[:120]}")

    db.commit()
    remaining = max(0, total_pending - len(aliments)) if not body.ids else 0
    return send_response(
        {
            "synced": len(synced),
            "not_found": not_found,
            "errors": errors,
            "remaining": remaining,
        },
        f"{len(synced)} alimentos sincronizados con USDA",
    )
