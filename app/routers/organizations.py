import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import (
    get_current_user, require_role_ids, _user_role_ids,
    SUPERADMIN, ADMIN, COACH,
)
from app.core.responses import send_response, send_error
from app.models.organization import Organization, OrganizationMember
from app.models.user import UserDetail

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class OrgCreate(BaseModel):
    name: str
    slug: Optional[str] = None

class OrgUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None

class MemberAdd(BaseModel):
    user_detail_id: str
    permissions: Optional[Dict[str, Any]] = None

class MemberPermissionsUpdate(BaseModel):
    permissions: Dict[str, Any]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_org(user_detail_id: str, db: Session) -> Optional[Organization]:
    """Return the org where this user_detail is owner, or a member."""
    org = db.query(Organization).filter(Organization.owner_id == user_detail_id).first()
    if org:
        return org
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_detail_id == user_detail_id
    ).first()
    if membership:
        return db.query(Organization).filter(Organization.id == membership.organization_id).first()
    return None


def _serialize_org(org: Organization, db: Session) -> dict:
    members = []
    for m in org.members:
        ud = m.user_detail
        members.append({
            "id": m.id,
            "user_detail_id": m.user_detail_id,
            "name": f"{ud.name} {ud.last_name or ''}".strip() if ud else "—",
            "permissions": m.permissions or {},
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        })
    owner = org.owner
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "is_active": org.is_active,
        "owner": {
            "id": owner.id,
            "name": f"{owner.name} {owner.last_name or ''}".strip() if owner else "—",
        } if owner else None,
        "members": members,
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/mine", summary="Mi organización")
def get_mine(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the organization the authenticated user belongs to (as owner or member)."""
    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    if not detail:
        return send_error("Perfil de usuario no encontrado", code=404)
    org = _get_user_org(detail.id, db)
    if not org:
        return send_error("No perteneces a ninguna organización", code=404)
    return send_response(_serialize_org(org, db), "OK")


@router.post("", summary="Crear organización (solo admin de plataforma)")
def create_org(
    data: OrgCreate,
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN)),
    db: Session = Depends(get_db),
):
    """Only platform admins can create organizations manually."""
    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    if not detail:
        return send_error("Perfil no encontrado", code=404)

    slug = data.slug or f"{data.name.lower().replace(' ', '-')[:40]}-{str(uuid.uuid4())[:8]}"
    org = Organization(
        id=str(uuid.uuid4()),
        name=data.name,
        slug=slug,
        owner_id=detail.id,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return send_response(_serialize_org(org, db), "Organización creada")


@router.patch("/{org_id}", summary="Editar organización")
def update_org(
    org_id: str,
    data: OrgUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Only the org owner or platform admin can edit."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return send_error("Organización no encontrada", code=404)

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    roles = _user_role_ids(current_user.id, db)
    is_admin = SUPERADMIN in roles or ADMIN in roles
    is_owner = detail and org.owner_id == detail.id

    if not (is_admin or is_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos")

    if data.name is not None:
        org.name = data.name
    if data.slug is not None:
        org.slug = data.slug
    if data.is_active is not None:
        org.is_active = data.is_active
    org.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(org)
    return send_response(_serialize_org(org, db), "Organización actualizada")


@router.get("/{org_id}/members", summary="Listar miembros de la organización")
def list_members(
    org_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return send_error("Organización no encontrada", code=404)

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    roles = _user_role_ids(current_user.id, db)
    is_admin = SUPERADMIN in roles or ADMIN in roles
    is_in_org = detail and (
        org.owner_id == detail.id
        or db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_detail_id == detail.id,
        ).first()
    )
    if not (is_admin or is_in_org):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos")

    return send_response(_serialize_org(org, db)["members"], "OK")


@router.post("/{org_id}/members", summary="Añadir coach a la organización")
def add_member(
    org_id: str,
    data: MemberAdd,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Only org owner or platform admin can add members."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return send_error("Organización no encontrada", code=404)

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    roles = _user_role_ids(current_user.id, db)
    is_admin = SUPERADMIN in roles or ADMIN in roles
    is_owner = detail and org.owner_id == detail.id

    if not (is_admin or is_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el dueño puede añadir miembros")

    # Prevent adding the owner as member
    if data.user_detail_id == org.owner_id:
        return send_error("El dueño ya forma parte de la organización")

    # Prevent duplicate
    existing = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_detail_id == data.user_detail_id,
    ).first()
    if existing:
        return send_error("Este usuario ya es miembro de la organización")

    # Verify the user_detail exists
    target = db.query(UserDetail).filter(UserDetail.id == data.user_detail_id).first()
    if not target:
        return send_error("Usuario no encontrado", code=404)

    member = OrganizationMember(
        organization_id=org_id,
        user_detail_id=data.user_detail_id,
        permissions=data.permissions or {},
    )
    db.add(member)
    db.commit()
    return send_response({"id": member.id}, "Miembro añadido")


class NewCoachCreate(BaseModel):
    name: str
    last_name: Optional[str] = None
    email: str
    password: str
    permissions: Optional[Dict[str, Any]] = None


@router.post("/{org_id}/members/create-coach", summary="Crear nuevo coach y añadirlo a la organización")
def create_coach_member(
    org_id: str,
    data: NewCoachCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Org owner or platform admin can create a new coach account and add them to the org."""
    from app.models.user import User, RoleUser
    from app.core.security import hash_password

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return send_error("Organización no encontrada", code=404)

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    roles = _user_role_ids(current_user.id, db)
    is_admin = SUPERADMIN in roles or ADMIN in roles
    is_owner = detail and org.owner_id == detail.id

    if not (is_admin or is_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el dueño puede crear miembros")

    if db.query(User).filter(User.email == data.email).first():
        return send_error("El email ya está registrado", code=400)

    if len(data.password) < 6:
        return send_error("La contraseña debe tener al menos 6 caracteres", code=400)

    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
    )
    db.add(user)
    db.flush()

    db.add(RoleUser(role_id=5, user_id=user.id))  # COACH role

    new_detail = UserDetail(
        user_id=user.id,
        name=data.name,
        last_name=data.last_name,
    )
    db.add(new_detail)
    db.flush()

    member = OrganizationMember(
        organization_id=org_id,
        user_detail_id=new_detail.id,
        permissions=data.permissions or {},
        joined_at=datetime.utcnow(),
    )
    db.add(member)
    db.commit()

    return send_response(
        {"user_detail_id": new_detail.id, "member_id": member.id, "email": data.email},
        "Coach creado y añadido a la organización",
    )


@router.patch("/{org_id}/members/{member_id}/permissions", summary="Actualizar permisos de un miembro")
def update_member_permissions(
    org_id: str,
    member_id: int,
    data: MemberPermissionsUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return send_error("Organización no encontrada", code=404)

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    roles = _user_role_ids(current_user.id, db)
    is_admin = SUPERADMIN in roles or ADMIN in roles
    is_owner = detail and org.owner_id == detail.id

    if not (is_admin or is_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el dueño puede editar permisos")

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not member:
        return send_error("Miembro no encontrado", code=404)

    member.permissions = data.permissions
    db.commit()
    return send_response({"id": member.id, "permissions": member.permissions}, "Permisos actualizados")


@router.delete("/{org_id}/members/{member_id}", summary="Eliminar miembro de la organización")
def remove_member(
    org_id: str,
    member_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return send_error("Organización no encontrada", code=404)

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    roles = _user_role_ids(current_user.id, db)
    is_admin = SUPERADMIN in roles or ADMIN in roles
    is_owner = detail and org.owner_id == detail.id

    if not (is_admin or is_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el dueño puede eliminar miembros")

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not member:
        return send_error("Miembro no encontrado", code=404)

    db.delete(member)
    db.commit()
    return send_response(None, "Miembro eliminado")
