from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.role import Role
from app.models.menu import Menu, MenuRole
from app.schemas.role import RoleCreateRequest, RoleUpdateRequest, MenuAssignRequest, RoleOut
from app.schemas.auth import MenuOut

router = APIRouter(prefix="/roles", tags=["Roles"])


def _get_or_404(db: Session, role_id: int) -> Role:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return role


@router.post("")
def create(data: RoleCreateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    role = Role(name=data.name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return RoleOut.model_validate(role)


@router.get("/search")
def find_all(
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Role)
    if search:
        q = q.filter(Role.name.ilike(f"%{search}%"))
    total = q.count()
    roles = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "data": [RoleOut.model_validate(r) for r in roles],
        "total": total,
        "page": page,
        "per_page": per_page,
        "last_page": (total + per_page - 1) // per_page,
    }


@router.get("/menus")
def menus_find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    menus = db.query(Menu).all()
    return [MenuOut.model_validate(m) for m in menus]


@router.post("/menus")
def menus_assign(data: MenuAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    _get_or_404(db, data.role_id)
    db.query(MenuRole).filter(MenuRole.role_id == data.role_id).delete()
    for menu_id in data.menu_ids:
        db.add(MenuRole(role_id=data.role_id, menu_id=menu_id))
    db.commit()
    return {"message": "Menús asignados correctamente"}


@router.get("/{id}/menus")
def menus_edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    _get_or_404(db, id)
    menu_roles = db.query(MenuRole).filter(MenuRole.role_id == id).all()
    return [mr.menu_id for mr in menu_roles]


@router.get("/{id}")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return RoleOut.model_validate(_get_or_404(db, id))


@router.put("/{id}")
def update(id: int, data: RoleUpdateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    role = _get_or_404(db, id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return RoleOut.model_validate(role)
