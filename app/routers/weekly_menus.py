from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.weekly_menu import WeeklyMenu, WeeklyMenuDay
from app.schemas.weekly_menu import WeeklyMenuCreate, WeeklyMenuUpdate

router = APIRouter(prefix="/weekly-menus", tags=["Weekly Menus"])


def _serialize(m: WeeklyMenu) -> dict:
    days = []
    for d in m.days:
        days.append({
            "day_index": d.day_index,
            "diet_id": d.diet_id,
            "diet_title": d.diet.title if d.diet else None,
            "calories": d.diet.calories if d.diet else None,
        })
    return {
        "id": m.id,
        "name": m.name,
        "description": m.description,
        "is_favorite": m.is_favorite,
        "days": days,
        "assigned_count": 0,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }


@router.get("", summary="Listar menús semanales")
def list_menus(
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    menus = db.query(WeeklyMenu).filter(WeeklyMenu.coach_id == current_user.id).order_by(WeeklyMenu.created_at.desc()).all()
    return send_response([_serialize(m) for m in menus], "OK")


@router.post("", summary="Crear menú semanal")
def create_menu(
    data: WeeklyMenuCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    menu = WeeklyMenu(
        name=data.name,
        description=data.description,
        coach_id=current_user.id,
    )
    db.add(menu)
    db.flush()

    for d in data.days:
        db.add(WeeklyMenuDay(
            menu_id=menu.id,
            day_index=d.day_index,
            diet_id=d.diet_id,
        ))

    db.commit()
    db.refresh(menu)
    return send_response(_serialize(menu), "Menú creado")


@router.get("/{id}", summary="Ver menú semanal")
def get_menu(
    id: str,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado", code=404)
    return send_response(_serialize(menu), "OK")


@router.put("/{id}", summary="Actualizar menú semanal")
def update_menu(
    id: str,
    data: WeeklyMenuUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado", code=404)

    if data.name is not None:
        menu.name = data.name
    if data.description is not None:
        menu.description = data.description
    if data.is_favorite is not None:
        menu.is_favorite = data.is_favorite

    if data.days is not None:
        db.query(WeeklyMenuDay).filter(WeeklyMenuDay.menu_id == id).delete()
        for d in data.days:
            db.add(WeeklyMenuDay(menu_id=id, day_index=d.day_index, diet_id=d.diet_id))

    db.commit()
    db.refresh(menu)
    return send_response(_serialize(menu), "Menú actualizado")


@router.patch("/{id}", summary="Actualización parcial (favorito)")
def patch_menu(
    id: str,
    data: WeeklyMenuUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado", code=404)
    if data.is_favorite is not None:
        menu.is_favorite = data.is_favorite
    if data.name is not None:
        menu.name = data.name
    if data.description is not None:
        menu.description = data.description
    db.commit()
    db.refresh(menu)
    return send_response(_serialize(menu), "OK")


@router.delete("/{id}", summary="Eliminar menú semanal")
def delete_menu(
    id: str,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado", code=404)
    db.delete(menu)
    db.commit()
    return send_response(None, "Menú eliminado")
