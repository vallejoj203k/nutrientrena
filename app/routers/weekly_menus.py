from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Union
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH, EDITOR_CONTENIDO_GLOBAL
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
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH, EDITOR_CONTENIDO_GLOBAL)),
):
    from app.models.client_menu import ClientMenu
    # Las copias por cliente no son plantillas: no aparecen en la biblioteca.
    assigned = db.query(ClientMenu.menu_id)
    menus = (
        db.query(WeeklyMenu)
        .filter(WeeklyMenu.coach_id == current_user.id, ~WeeklyMenu.id.in_(assigned))
        .order_by(WeeklyMenu.created_at.desc())
        .all()
    )
    return send_response([_serialize(m) for m in menus], "OK")


@router.post("", summary="Crear menú semanal")
def create_menu(
    data: WeeklyMenuCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH, EDITOR_CONTENIDO_GLOBAL)),
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
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH, EDITOR_CONTENIDO_GLOBAL)),
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
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH, EDITOR_CONTENIDO_GLOBAL)),
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
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH, EDITOR_CONTENIDO_GLOBAL)),
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
    # Admite el id de usuario (users.id) o el UUID del UserDetail del cliente.
    client_id: Union[int, str]


def _resolve_client(db: Session, client_id):
    """Devuelve (User, UserDetail) a partir de users.id o del UUID de UserDetail."""
    from app.models.user import User, UserDetail

    detail = None
    user = None
    if isinstance(client_id, int) or str(client_id).isdigit():
        user = db.query(User).filter(User.id == int(client_id)).first()
        if user:
            detail = db.query(UserDetail).filter(UserDetail.user_id == user.id).first()
    else:
        detail = db.query(UserDetail).filter(UserDetail.id == str(client_id)).first()
        if detail:
            user = db.query(User).filter(User.id == detail.user_id).first()
    return user, detail


@router.post("/{id}/assign", summary="Asignar menú semanal a un cliente", description="Deja el menú como vigente del cliente y copia las dietas de cada día (una copia por dieta distinta).")
def assign_menu(
    id: str,
    body: _MenuAssignBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.routers.nutrition.diets import copy_diet_to_user
    from app.models.client_menu import ClientMenu

    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado", code=404)
    client, detail = _resolve_client(db, body.client_id)
    if not client:
        return send_error("Cliente no encontrado", code=404)

    # Copiar cada dieta distinta del menú una sola vez
    mapping: dict = {}
    for day in menu.days:
        if day.diet and day.diet_id not in mapping:
            copy = copy_diet_to_user(db, day.diet, client.id, current_user.id)
            mapping[day.diet_id] = copy.id
    if not mapping:
        return send_error("El menú no tiene dietas para asignar", code=422)

    # El menú vigente del cliente es una copia propia que apunta a SUS dietas:
    # así el coach puede editar cada día desde la ficha del cliente sin tocar
    # la plantilla de la biblioteca ni a los demás clientes.
    if detail:
        client_menu = WeeklyMenu(
            name=menu.name,
            description=menu.description,
            coach_id=current_user.id,
            organization_id=menu.organization_id,
        )
        db.add(client_menu)
        db.flush()
        for day in menu.days:
            db.add(WeeklyMenuDay(
                menu_id=client_menu.id,
                day_index=day.day_index,
                name=day.name,
                diet_id=mapping.get(day.diet_id),
            ))
        db.add(ClientMenu(
            client_user_detail_id=detail.id,
            menu_id=client_menu.id,
            assigned_by_user_id=current_user.id,
        ))
    db.commit()
    return send_response({"copied_diets": len(mapping)}, "Menú asignado")


class _MenuDayBody(BaseModel):
    diet_id: Optional[str] = None


@router.put("/{id}/days/{day_index}", summary="Fijar la dieta de un día del menú")
def set_menu_day(
    id: str,
    day_index: int,
    body: _MenuDayBody,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado", code=404)
    if day_index < 0 or day_index > 6:
        return send_error("Día no válido", code=422)
    day = (
        db.query(WeeklyMenuDay)
        .filter(WeeklyMenuDay.menu_id == id, WeeklyMenuDay.day_index == day_index)
        .first()
    )
    if day:
        day.diet_id = body.diet_id
    else:
        db.add(WeeklyMenuDay(menu_id=id, day_index=day_index, diet_id=body.diet_id))
    db.commit()
    db.refresh(menu)
    return send_response(_serialize(menu), "Día actualizado")


@router.get("/client/{client_id}", summary="Menú semanal vigente de un cliente")
def client_menu(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.core.dependencies import verify_client_access
    from app.models.client_menu import ClientMenu

    verify_client_access(client_id, current_user, db)
    cm = (
        db.query(ClientMenu)
        .filter(ClientMenu.client_user_detail_id == client_id)
        .order_by(ClientMenu.assigned_at.desc(), ClientMenu.id.desc())
        .first()
    )
    if not cm:
        return send_response(None, "Sin menú asignado")
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == cm.menu_id).first()
    if not menu:
        return send_response(None, "Sin menú asignado")
    data = _serialize(menu)
    data["assigned_at"] = cm.assigned_at
    return send_response(data, "OK")


@router.delete("/client/{client_id}", summary="Quitar el menú semanal asignado a un cliente")
def unassign_client_menu(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.core.dependencies import verify_client_access
    from app.models.client_menu import ClientMenu

    verify_client_access(client_id, current_user, db)
    rows = db.query(ClientMenu).filter(ClientMenu.client_user_detail_id == client_id).all()
    if not rows:
        return send_error("Este cliente no tiene menú asignado", code=404)
    for r in rows:
        db.delete(r)
    db.commit()
    return send_response({"removed": len(rows)}, "Menú retirado del cliente")


@router.delete("/{id}", summary="Eliminar menú semanal")
def delete_menu(
    id: str,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH, EDITOR_CONTENIDO_GLOBAL)),
):
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == id).first()
    if not menu:
        return send_error("Menú no encontrado", code=404)
    db.delete(menu)
    db.commit()
    return send_response(None, "Menú eliminado")
