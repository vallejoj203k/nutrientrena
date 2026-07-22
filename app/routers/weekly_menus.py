from fastapi import APIRouter, Depends
from pydantic import BaseModel
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
            "name": d.name,
            "diet_id": d.diet_id,
            "diet_title": d.diet.title if d.diet else None,
            "calories": d.diet.calories if d.diet else None,
            "proteins": d.diet.detail.proteins if d.diet and d.diet.detail else None,
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
            name=d.name,
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
            db.add(WeeklyMenuDay(menu_id=id, day_index=d.day_index, name=d.name, diet_id=d.diet_id))

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


class _MenuAssignBody(BaseModel):
    client_id: int  # users.id del cliente


@router.post("/{id}/assign", summary="Asignar menú semanal a un cliente", description="Copia al cliente las dietas de cada día del menú (una copia por dieta distinta).")
def assign_menu(
    id: str,
    body: _MenuAssignBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.routers.nutrition.diets import copy_diet_to_user
    from app.models.user import User

    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado", code=404)
    client = db.query(User).filter(User.id == body.client_id).first()
    if not client:
        return send_error("Cliente no encontrado", code=404)

    # Copiar cada dieta distinta del menú una sola vez
    seen: set = set()
    copied = 0
    for day in menu.days:
        if day.diet and day.diet_id not in seen:
            seen.add(day.diet_id)
            copy_diet_to_user(db, day.diet, client.id, current_user.id)
            copied += 1
    if not copied:
        return send_error("El menú no tiene dietas para asignar", code=422)
    db.commit()
    return send_response({"copied_diets": copied}, "Menú asignado")


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


# ── Asignar menú semanal a un cliente ──────────────────────────────────────────
class _AssignMenuBody(BaseModel):
    client_id: str  # UserDetail UUID del cliente


@router.post("/{id}/assign", summary="Asignar menú a cliente", description="Asigna este menú semanal a un cliente; pasa a ser su menú vigente.")
def assign_menu_to_client(id: str, body: _AssignMenuBody, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    from app.models.user import UserDetail
    from app.models.client_menu import ClientMenu
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado")
    client = db.query(UserDetail).filter(UserDetail.id == body.client_id).first()
    if not client:
        return send_error("Cliente no encontrado")
    db.add(ClientMenu(client_user_detail_id=body.client_id, menu_id=id, assigned_by_user_id=current_user.id))
    db.commit()
    return send_response(None, "Menú asignado al cliente")
