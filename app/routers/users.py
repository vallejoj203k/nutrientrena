from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import (
    require_role_ids, verify_client_access, filter_clients_by_role,
    SUPERADMIN, ADMIN, SETTER, CLOSER, COACH,
)
from app.core.security import hash_password
from app.core.responses import send_response, send_error
from app.models.user import User, UserDetail, RoleUser, UserParent
from app.models.role import Role, CLIENT
from app.models.parameter import ParameterDetail, Parameter
from app.schemas.user import (
    UserCreateRequest, UserUpdateRequest, UserStateRequest,
    UserAssignRequest, WeeksTrainingRequest, UserDetailOut,
)
from pydantic import BaseModel as _BaseModel


class _PhotoRequest(_BaseModel):
    photo: str

router = APIRouter(prefix="/users", tags=["Users"])


def _get_detail_or_404(db: Session, detail_id: str):
    return db.query(UserDetail).filter(UserDetail.id == detail_id).first()


def _serialize(detail: UserDetail, db: Session) -> dict:
    out = UserDetailOut.model_validate(detail).model_dump()
    role_users = db.query(RoleUser).filter(RoleUser.user_id == detail.user_id).all()
    out["roles"] = [{"id": ru.role_id, "name": ru.role.name if ru.role else None} for ru in role_users]
    out["email"] = detail.user.email if detail.user else None
    # Nested parameter objects so the frontend can show names, not just ids
    out["gender"] = {"id": detail.gender.id, "name": detail.gender.description} if detail.gender else None
    out["activity"] = {"id": detail.activity.id, "name": detail.activity.description} if detail.activity else None
    out["objective"] = {"id": detail.objective.id, "name": detail.objective.description} if detail.objective else None
    return out


# ── Create: superadmin, admin, setter ─────────────────────────────────────────
@router.post("", summary="Crear usuario", description="Crea un nuevo usuario con rol, perfil e instructor asignado.")
def create(
    data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, COACH)),
):
    from app.core.dependencies import _user_role_ids
    creator_roles = _user_role_ids(current_user.id, db)
    creator_is_coach_only = COACH in creator_roles and ADMIN not in creator_roles and SUPERADMIN not in creator_roles
    if creator_is_coach_only and data.role_id not in (6,):  # coaches can only create clients (role 6)
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Los coaches solo pueden crear clientes")

    if db.query(User).filter(User.email == data.email).first():
        return send_error("El email ya está registrado", code=400)

    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
    )
    db.add(user)
    db.flush()

    db.add(RoleUser(role_id=data.role_id, user_id=user.id))

    detail = UserDetail(
        user_id=user.id,
        name=data.name,
        last_name=data.last_name,
        phone=data.phone,
        height=data.height,
        weight=data.weight,
        age=data.age,
        body_fat=data.body_fat,
        allergies=data.allergies,
        intolerances=data.intolerances,
        dislikes=data.dislikes,
        injuries=data.injuries,
        equipment=data.equipment,
        food_preferences=data.food_preferences,
        occupation=data.occupation,
        country_code=data.country_code,
        gender_id=data.gender_id,
        activity_id=data.activity_id,
        status_id=data.status_id,
        objective_id=data.objective_id,
        defecit=data.defecit,
        excedente=data.excedente,
    )
    db.add(detail)
    db.flush()

    # If the creator is a coach, auto-assign themselves; otherwise use the supplied instructor
    from app.core.dependencies import _user_role_ids
    creator_roles = _user_role_ids(current_user.id, db)
    if COACH in creator_roles and ADMIN not in creator_roles and SUPERADMIN not in creator_roles:
        instructor_detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    elif data.instructor:
        instructor_detail = db.query(UserDetail).filter(UserDetail.id == data.instructor).first()
    else:
        instructor_detail = None

    if instructor_detail:
        db.add(UserParent(
            user_detail_id=detail.id,
            parent_user_detail_id=instructor_detail.id,
        ))

    db.commit()
    db.refresh(detail)
    return send_response(_serialize(detail, db), "Usuario creado")


# ── Assign coach: superadmin, admin ───────────────────────────────────────────
@router.post("/assign", summary="Asignar coach a cliente", description="Asigna o reasigna un coach a un cliente existente.")
def assigned(
    data: UserAssignRequest,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN)),
):
    client_detail = _get_detail_or_404(db, data.user_id)
    if not client_detail:
        return send_error("Usuario no encontrado")

    instructor_detail = _get_detail_or_404(db, data.user_parent_id)
    if not instructor_detail:
        return send_error("Instructor no encontrado")

    existing = db.query(UserParent).filter(
        UserParent.user_detail_id == data.user_id
    ).first()
    if existing:
        existing.parent_user_detail_id = data.user_parent_id
    else:
        db.add(UserParent(
            user_detail_id=data.user_id,
            parent_user_detail_id=data.user_parent_id,
        ))
    db.commit()
    return send_response(None, "Asignado correctamente")


# ── Update training weeks: admin, coach ───────────────────────────────────────
@router.post("/weeks", summary="Actualizar semanas de entrenamiento", description="Establece las fechas de inicio y fin del periodo de entrenamiento del cliente.")
def weeks_training(
    data: WeeksTrainingRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    detail = _get_detail_or_404(db, data.client_id)
    if not detail:
        return send_error("Usuario no encontrado")
    verify_client_access(data.client_id, current_user, db)
    detail.start_date = data.start_date
    detail.end_date = data.end_date
    db.commit()
    return send_response(None, "Semanas actualizadas")


# ── Find all by role slug: staff only ─────────────────────────────────────────
@router.get("/{slug}/findAll", summary="Listar usuarios por rol", description="Retorna todos los usuarios del rol indicado (slug). Coaches solo ven sus clientes.")
def find_all(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    role = db.query(Role).filter(Role.slug == slug).first()
    if not role:
        return send_error("Rol no encontrado")

    role_users = db.query(RoleUser).filter(RoleUser.role_id == role.id).all()
    user_ids = [ru.user_id for ru in role_users]
    details = db.query(UserDetail).filter(UserDetail.user_id.in_(user_ids)).all()

    # Coaches only see their assigned clients when slug=client
    if slug == "client":
        details = filter_clients_by_role(details, current_user, db)

    return send_response([_serialize(d, db) for d in details], "OK")


# ── Search: staff only ────────────────────────────────────────────────────────
@router.get("/{slug}/search", summary="Buscar usuarios", description="Búsqueda paginada de usuarios por nombre dentro de un rol.")
def search(
    slug: str,
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    role = db.query(Role).filter(Role.slug == slug).first()
    if not role:
        return send_error("Rol no encontrado")

    role_user_ids = [ru.user_id for ru in db.query(RoleUser).filter(RoleUser.role_id == role.id).all()]
    q = db.query(UserDetail).filter(UserDetail.user_id.in_(role_user_ids))

    if search:
        q = q.filter(
            UserDetail.name.ilike(f"%{search}%")
            | UserDetail.last_name.ilike(f"%{search}%")
        )

    all_details = q.all()

    # Coaches only see their own clients
    if slug == "client":
        all_details = filter_clients_by_role(all_details, current_user, db)

    total = len(all_details)
    start = (page - 1) * per_page
    details = all_details[start: start + per_page]

    return send_response(
        {
            "data": [_serialize(d, db) for d in details],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": max(1, (total + per_page - 1) // per_page),
        },
        "OK",
    )


# ── Kanban: staff only (coaches see only their clients) ───────────────────────
@router.get("/kanban", summary="Vista kanban de clientes", description="Clientes agrupados por estado para la vista kanban. Coaches solo ven sus clientes.")
def kanban(
    coach_id: Optional[str] = Query(None, description="Filtrar por UserDetail UUID del coach"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    client_user_ids = [
        ru.user_id for ru in db.query(RoleUser).filter(RoleUser.role_id == CLIENT).all()
    ]
    q = db.query(UserDetail).filter(UserDetail.user_id.in_(client_user_ids))

    if coach_id:
        assigned_ids = [
            up.user_detail_id for up in
            db.query(UserParent).filter(UserParent.parent_user_detail_id == coach_id).all()
        ]
        q = q.filter(UserDetail.id.in_(assigned_ids))

    clients = q.all()
    clients = filter_clients_by_role(clients, current_user, db)

    groups: dict[Optional[int], list] = {}
    for c in clients:
        key = c.status_id
        if key not in groups:
            groups[key] = []
        groups[key].append(_serialize(c, db))

    estado_param = db.query(Parameter).filter(
        Parameter.description == "Estado del Cliente"
    ).first()
    state_names: dict[int, str] = {}
    if estado_param:
        for pd in db.query(ParameterDetail).filter(
            ParameterDetail.parameter_id == estado_param.id
        ).all():
            state_names[pd.id] = pd.description

    columns = []
    if None in groups:
        columns.append({
            "status_id": None,
            "status_name": "Sin estado",
            "total": len(groups[None]),
            "clients": groups[None],
        })
    for sid in sorted(k for k in groups if k is not None):
        columns.append({
            "status_id": sid,
            "status_name": state_names.get(sid, str(sid)),
            "total": len(groups[sid]),
            "clients": groups[sid],
        })

    return send_response({"columns": columns, "total_clients": len(clients)}, "OK")


# ── Report: any staff ─────────────────────────────────────────────────────────
@router.get("/report", summary="Reporte de usuarios", description="Total de clientes asignados al coach o administrador.")
def report_users(
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    current_detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    from app.core.dependencies import _user_role_ids
    user_roles = _user_role_ids(current_user.id, db)

    if SUPERADMIN in user_roles or ADMIN in user_roles:
        total = db.query(UserDetail).count()
    else:
        parent_ids = db.query(UserParent).filter(
            UserParent.parent_user_detail_id == current_detail.id
        ).all() if current_detail else []
        total = len(parent_ids)

    return send_response({"total": total}, "OK")


# ── Get by ID: staff only, coaches restricted to own clients ──────────────────
@router.get("/{id}/edit", summary="Ver perfil de usuario", description="Retorna el perfil completo de un usuario por su ID (UserDetail UUID).")
def edit(
    id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    detail = _get_detail_or_404(db, id)
    if not detail:
        return send_error("Usuario no encontrado")
    verify_client_access(id, current_user, db)
    return send_response(_serialize(detail, db), "OK")


# ── Update: admin, coach (own clients only) ───────────────────────────────────
@router.put("/{id}/update", summary="Actualizar usuario", description="Modifica datos del perfil, email, contraseña o rol del usuario.")
def updated(
    id: str,
    data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    detail = _get_detail_or_404(db, id)
    if not detail:
        return send_error("Usuario no encontrado")
    verify_client_access(id, current_user, db)

    user_fields = {}
    if data.email is not None:
        user_fields["email"] = data.email
    if data.password is not None:
        user_fields["password"] = hash_password(data.password)
    for field, value in user_fields.items():
        setattr(detail.user, field, value)

    detail_fields = data.model_dump(exclude_unset=True, exclude={"email", "password", "role_id"})
    for field, value in detail_fields.items():
        setattr(detail, field, value)

    if data.role_id is not None:
        from app.core.dependencies import _user_role_ids
        updater_roles = _user_role_ids(current_user.id, db)
        updater_is_coach_only = COACH in updater_roles and ADMIN not in updater_roles and SUPERADMIN not in updater_roles
        if updater_is_coach_only and data.role_id != 6:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Los coaches solo pueden asignar el rol de cliente")
        role_user = db.query(RoleUser).filter(RoleUser.user_id == detail.user_id).first()
        if role_user:
            role_user.role_id = data.role_id
        else:
            db.add(RoleUser(role_id=data.role_id, user_id=detail.user_id))

    db.commit()
    db.refresh(detail)
    return send_response(_serialize(detail, db), "Usuario actualizado")


# ── Update photo ─────────────────────────────────────────────────────────────
@router.patch("/{id}/photo", summary="Actualizar foto de perfil", description="Actualiza la URL de la foto de perfil del usuario.")
def update_photo(
    id: str,
    data: _PhotoRequest,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    detail = _get_detail_or_404(db, id)
    if not detail:
        return send_error("Usuario no encontrado", code=404)
    detail.photo = data.photo
    db.commit()
    db.refresh(detail)
    return send_response(_serialize(detail, db), "Foto actualizada")


# ── Change state: admin, setter, closer ───────────────────────────────────────
@router.put("/{id}/change", summary="Cambiar estado de usuario", description="Actualiza el estado del usuario (activo, inactivo, etc.).")
def change_state(
    id: str,
    data: UserStateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER)),
):
    detail = _get_detail_or_404(db, id)
    if not detail:
        return send_error("Usuario no encontrado")
    detail.status_id = data.status_id
    db.commit()
    return send_response(None, "Estado actualizado")
