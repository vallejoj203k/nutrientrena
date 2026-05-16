from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.core.responses import send_response, send_error
from app.models.user import User, UserDetail, RoleUser, UserParent
from app.models.role import Role, CLIENT
from app.models.parameter import ParameterDetail, Parameter
from app.schemas.user import (
    UserCreateRequest, UserUpdateRequest, UserStateRequest,
    UserAssignRequest, WeeksTrainingRequest, UserDetailOut,
)

router = APIRouter(prefix="/users", tags=["Users"])


def _get_detail_or_404(db: Session, detail_id: str):
    detail = db.query(UserDetail).filter(UserDetail.id == detail_id).first()
    return detail


def _serialize(detail: UserDetail, db: Session) -> dict:
    out = UserDetailOut.model_validate(detail).model_dump()
    role_users = db.query(RoleUser).filter(RoleUser.user_id == detail.user_id).all()
    out["roles"] = [{"id": ru.role_id, "name": ru.role.name if ru.role else None} for ru in role_users]
    out["email"] = detail.user.email if detail.user else None
    return out


@router.post("")
def create(data: UserCreateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
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

    if data.instructor:
        instructor_detail = db.query(UserDetail).filter(UserDetail.id == data.instructor).first()
        if instructor_detail:
            db.add(UserParent(
                user_detail_id=detail.id,
                parent_user_detail_id=instructor_detail.id,
            ))

    db.commit()
    db.refresh(detail)
    return send_response(_serialize(detail, db), "Usuario creado")


@router.post("/assign")
def assigned(data: UserAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
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


@router.post("/weeks")
def weeks_training(data: WeeksTrainingRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    detail = _get_detail_or_404(db, data.client_id)
    if not detail:
        return send_error("Usuario no encontrado")
    detail.start_date = data.start_date
    detail.end_date = data.end_date
    db.commit()
    return send_response(None, "Semanas actualizadas")


@router.get("/{slug}/findAll")
def find_all(slug: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    role = db.query(Role).filter(Role.slug == slug).first()
    if not role:
        return send_error("Rol no encontrado")

    role_users = db.query(RoleUser).filter(RoleUser.role_id == role.id).all()
    user_ids = [ru.user_id for ru in role_users]
    details = db.query(UserDetail).filter(UserDetail.user_id.in_(user_ids)).all()
    return send_response([_serialize(d, db) for d in details], "OK")


@router.get("/{slug}/search")
def search(
    slug: str,
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
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

    total = q.count()
    details = q.offset((page - 1) * per_page).limit(per_page).all()
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


@router.get("/kanban")
def kanban(
    coach_id: Optional[str] = Query(None, description="Filtrar por UserDetail UUID del coach"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    # Obtener todos los IDs de usuarios con rol cliente
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

    # Agrupar por status_id
    groups: dict[Optional[int], list] = {}
    for c in clients:
        key = c.status_id
        if key not in groups:
            groups[key] = []
        groups[key].append(_serialize(c, db))

    # Obtener los nombres de estado del Cliente
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
    # Columna sin estado
    if None in groups:
        columns.append({
            "status_id": None,
            "status_name": "Sin estado",
            "total": len(groups[None]),
            "clients": groups[None],
        })
    # Columnas con estado, en orden de ID
    for sid in sorted(k for k in groups if k is not None):
        columns.append({
            "status_id": sid,
            "status_name": state_names.get(sid, str(sid)),
            "total": len(groups[sid]),
            "clients": groups[sid],
        })

    return send_response(
        {"columns": columns, "total_clients": len(clients)},
        "OK",
    )


@router.get("/report")
def report_users(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    current_detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()

    role_users = db.query(RoleUser).filter(RoleUser.user_id == current_user.id).all()
    role_ids = [ru.role_id for ru in role_users]
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    is_admin = any(r.slug == "admin" for r in roles)

    if is_admin:
        total = db.query(UserDetail).count()
    else:
        parent_ids = db.query(UserParent).filter(
            UserParent.parent_user_detail_id == current_detail.id
        ).all() if current_detail else []
        client_ids = [p.user_detail_id for p in parent_ids]
        total = len(client_ids)

    return send_response({"total": total}, "OK")


@router.get("/{id}/edit")
def edit(id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    detail = _get_detail_or_404(db, id)
    if not detail:
        return send_error("Usuario no encontrado")
    return send_response(_serialize(detail, db), "OK")


@router.put("/{id}/update")
def updated(id: str, data: UserUpdateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    detail = _get_detail_or_404(db, id)
    if not detail:
        return send_error("Usuario no encontrado")

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
        role_user = db.query(RoleUser).filter(RoleUser.user_id == detail.user_id).first()
        if role_user:
            role_user.role_id = data.role_id
        else:
            db.add(RoleUser(role_id=data.role_id, user_id=detail.user_id))

    db.commit()
    db.refresh(detail)
    return send_response(_serialize(detail, db), "Usuario actualizado")


@router.put("/{id}/change")
def change_state(id: str, data: UserStateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    detail = _get_detail_or_404(db, id)
    if not detail:
        return send_error("Usuario no encontrado")
    detail.status_id = data.status_id
    db.commit()
    return send_response(None, "Estado actualizado")
