from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN
from app.core.responses import send_response, send_error
from app.models.role import Role
from slugify import slugify
from app.models.menu import Menu, MenuRole
from app.schemas.role import RoleCreateRequest, RoleUpdateRequest, MenuAssignRequest, RoleOut
from app.schemas.auth import MenuOut

router = APIRouter(prefix="/roles", tags=["Roles"])


def _get_or_404(db: Session, role_id: int):
    return db.query(Role).filter(Role.id == role_id).first()


@router.post("", summary="Crear rol", description="Crea un nuevo rol de usuario (solo superadmin).")
def create(data: RoleCreateRequest, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN))):
    slug = slugify(data.slug or data.name)
    role = Role(name=data.name, slug=slug)
    db.add(role)
    db.commit()
    db.refresh(role)
    return send_response(RoleOut.model_validate(role).model_dump(), "Rol creado")


@router.get("/search", summary="Buscar roles", description="Búsqueda paginada de roles por nombre.")
def find_all(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN)),
):
    q = db.query(Role)
    if search:
        q = q.filter(Role.name.ilike(f"%{search}%"))
    total = q.count()
    roles = q.offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [RoleOut.model_validate(r).model_dump() for r in roles],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": (total + per_page - 1) // per_page,
        },
        "OK",
    )


@router.get("/menus", summary="Listar menús disponibles", description="Retorna todos los menús del sistema para asignar a roles.")
def menus_find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN))):
    menus = db.query(Menu).all()
    return send_response([MenuOut.model_validate(m).model_dump() for m in menus], "OK")


@router.post("/menus", summary="Asignar menús a rol", description="Asigna o reemplaza los menús accesibles para un rol.")
def menus_assign(data: MenuAssignRequest, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN))):
    if not _get_or_404(db, data.role_id):
        return send_error("Rol no encontrado")
    db.query(MenuRole).filter(MenuRole.role_id == data.role_id).delete()
    for menu_id in data.menu_ids:
        db.add(MenuRole(role_id=data.role_id, menu_id=menu_id))
    db.commit()
    return send_response(None, "Menús asignados correctamente")


@router.get("/{id}/menus", summary="Menús del rol", description="Retorna los IDs de menús asignados a un rol.")
def menus_edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN))):
    if not _get_or_404(db, id):
        return send_error("Rol no encontrado")
    menu_roles = db.query(MenuRole).filter(MenuRole.role_id == id).all()
    return send_response([mr.menu_id for mr in menu_roles], "OK")


@router.get("/{id}", summary="Ver rol", description="Retorna el detalle de un rol por su ID.")
def edit(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN))):
    role = _get_or_404(db, id)
    if not role:
        return send_error("Rol no encontrado")
    return send_response(RoleOut.model_validate(role).model_dump(), "OK")


@router.put("/{id}", summary="Actualizar rol", description="Modifica el nombre o slug de un rol existente.")
def update(id: int, data: RoleUpdateRequest, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN))):
    role = _get_or_404(db, id)
    if not role:
        return send_error("Rol no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return send_response(RoleOut.model_validate(role).model_dump(), "Rol actualizado")
