from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN
from app.core.responses import send_response, send_error
from app.models.user import UserDetail, UserParent
from app.models.team_member import TeamMember

router = APIRouter(prefix="/team", tags=["Team"])


class TeamMemberCreateRequest(BaseModel):
    user_detail_id: Optional[str] = None
    member_name: Optional[str] = None
    member_email: Optional[str] = None
    role_label: Optional[str] = None
    hours_week: Optional[int] = None
    salary_fijo: Optional[float] = None
    commission: Optional[float] = None
    variable_type: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    permissions: Optional[str] = None


class TeamMemberUpdateRequest(BaseModel):
    member_name: Optional[str] = None
    member_email: Optional[str] = None
    role_label: Optional[str] = None
    hours_week: Optional[int] = None
    salary_fijo: Optional[float] = None
    commission: Optional[float] = None
    variable_type: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    permissions: Optional[str] = None


def _serialize(member: TeamMember, db: Session) -> dict:
    ud: UserDetail = member.user_detail
    client_count = 0
    if ud:
        client_count = db.query(UserParent).filter(
            UserParent.parent_user_detail_id == member.user_detail_id
        ).count()

    name = (ud.name if ud else None) or member.member_name or ""
    last_name = (ud.last_name if ud else None) or ""
    email = (ud.user.email if ud and ud.user else None) or member.member_email or ""
    photo = ud.photo if ud else None

    return {
        "id": member.id,
        "user_detail_id": member.user_detail_id,
        "member_name": member.member_name,
        "member_email": member.member_email,
        "role_label": member.role_label,
        "hours_week": member.hours_week,
        "salary_fijo": member.salary_fijo,
        "commission": member.commission,
        "variable_type": member.variable_type,
        "currency": member.currency or "EUR",
        "notes": member.notes,
        "permissions": member.permissions,
        "created_at": member.created_at.isoformat() if member.created_at else None,
        "name": name,
        "last_name": last_name,
        "email": email,
        "photo": photo,
        "client_count": client_count,
    }


# ── GET /team ─────────────────────────────────────────────────────────────────
@router.get("", summary="Listar miembros del equipo")
def list_team(
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN)),
):
    members = db.query(TeamMember).all()
    return send_response(
        data=[_serialize(m, db) for m in members],
        message="Equipo obtenido correctamente",
    )


# ── POST /team ────────────────────────────────────────────────────────────────
@router.post("", summary="Crear miembro del equipo")
def create_team_member(
    data: TeamMemberCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN)),
):
    if not data.user_detail_id and not data.member_name:
        return send_error("Se requiere user_detail_id o member_name", code=400)

    # If user_detail_id provided, verify it exists
    if data.user_detail_id:
        ud = db.query(UserDetail).filter(UserDetail.id == data.user_detail_id).first()
        if not ud:
            return send_error("Usuario no encontrado", code=404)
        # Try to find by email if not already set
        existing = db.query(TeamMember).filter(
            TeamMember.user_detail_id == data.user_detail_id
        ).first()
        if existing:
            return send_error("Este usuario ya es miembro del equipo", code=400)
    else:
        # Try to auto-link by email
        linked_id = None
        if data.member_email:
            from app.models.user import User
            user = db.query(User).filter(User.email == data.member_email).first()
            if user and user.user_detail:
                linked_id = user.user_detail.id
        data_dict = data.dict()
        data_dict['user_detail_id'] = linked_id

    member = TeamMember(
        user_detail_id=data.user_detail_id,
        member_name=data.member_name,
        member_email=data.member_email,
        role_label=data.role_label,
        hours_week=data.hours_week,
        salary_fijo=data.salary_fijo,
        commission=data.commission,
        variable_type=data.variable_type,
        currency=data.currency or 'EUR',
        notes=data.notes,
        permissions=data.permissions,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return send_response(
        data=_serialize(member, db),
        message="Miembro del equipo creado correctamente",
    )


# ── PUT /team/{id} ────────────────────────────────────────────────────────────
@router.put("/{id}", summary="Actualizar miembro del equipo")
def update_team_member(
    id: int,
    data: TeamMemberUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN)),
):
    member = db.query(TeamMember).filter(TeamMember.id == id).first()
    if not member:
        return send_error("Miembro del equipo no encontrado", code=404)

    if data.member_name is not None:
        member.member_name = data.member_name
    if data.member_email is not None:
        member.member_email = data.member_email
    if data.role_label is not None:
        member.role_label = data.role_label
    if data.hours_week is not None:
        member.hours_week = data.hours_week
    if data.salary_fijo is not None:
        member.salary_fijo = data.salary_fijo
    if data.commission is not None:
        member.commission = data.commission
    if data.variable_type is not None:
        member.variable_type = data.variable_type
    if data.currency is not None:
        member.currency = data.currency
    if data.notes is not None:
        member.notes = data.notes
    if data.permissions is not None:
        member.permissions = data.permissions

    db.commit()
    db.refresh(member)

    return send_response(
        data=_serialize(member, db),
        message="Miembro del equipo actualizado correctamente",
    )


# ── DELETE /team/{id} ─────────────────────────────────────────────────────────
@router.delete("/{id}", summary="Eliminar miembro del equipo")
def delete_team_member(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN)),
):
    member = db.query(TeamMember).filter(TeamMember.id == id).first()
    if not member:
        return send_error("Miembro del equipo no encontrado", code=404)

    db.delete(member)
    db.commit()

    return send_response(
        data={"id": id},
        message="Miembro del equipo eliminado correctamente",
    )
