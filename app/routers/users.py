from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from slugify import slugify

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.core.responses import send_response, send_error
from app.models.user import User
from app.schemas.user import UserCreateRequest, UserUpdateRequest, UserStateRequest, UserAssignRequest, WeeksTrainingRequest, UserOut

router = APIRouter(prefix="/users", tags=["Users"])


def _get_or_404(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return user


@router.post("")
def create(data: UserCreateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(User).filter(User.email == data.email).first():
        return send_error("El email ya está registrado", code=400)

    slug_base = slugify(f"{data.name} {data.last_name or ''}".strip())
    slug = slug_base
    counter = 1
    while db.query(User).filter(User.slug == slug).first():
        slug = f"{slug_base}-{counter}"
        counter += 1

    user = User(
        **data.model_dump(exclude={"password"}),
        password=hash_password(data.password),
        slug=slug,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return send_response(UserOut.model_validate(user).model_dump(), "Usuario creado")


@router.post("/assign")
def assigned(data: UserAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, data.user_id)
    if not user:
        return send_error("Usuario no encontrado")
    user.instructor_id = data.instructor_id
    db.commit()
    return send_response(None, "Asignado correctamente")


@router.post("/weeks")
def weeks_training(data: WeeksTrainingRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, data.user_id)
    if not user:
        return send_error("Usuario no encontrado")
    user.notes = str(data.weeks)
    db.commit()
    return send_response(None, "Semanas actualizadas")


@router.get("/{slug}/findAll")
def find_all(slug: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    instructor = db.query(User).filter(User.slug == slug).first()
    if not instructor:
        return send_error("Instructor no encontrado")
    clients = db.query(User).filter(User.instructor_id == instructor.id).all()
    return send_response([UserOut.model_validate(c).model_dump() for c in clients], "OK")


@router.get("/{slug}/search")
def search(
    slug: str,
    search: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    instructor = db.query(User).filter(User.slug == slug).first()
    if not instructor:
        return send_error("Instructor no encontrado")

    q = db.query(User).filter(User.instructor_id == instructor.id)
    if search:
        q = q.filter((User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")))
    total = q.count()
    users = q.offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [UserOut.model_validate(u).model_dump() for u in users],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": (total + per_page - 1) // per_page,
        },
        "OK",
    )


@router.get("/report")
def report_users(db: Session = Depends(get_db), _=Depends(get_current_user)):
    total = db.query(User).count()
    active = db.query(User).filter(User.state == 1).count()
    return send_response({"total": total, "active": active, "inactive": total - active}, "OK")


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, id)
    if not user:
        return send_error("Usuario no encontrado")
    return send_response(UserOut.model_validate(user).model_dump(), "OK")


@router.put("/{id}/update")
def updated(id: int, data: UserUpdateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, id)
    if not user:
        return send_error("Usuario no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return send_response(UserOut.model_validate(user).model_dump(), "Usuario actualizado")


@router.put("/{id}/change")
def change_state(id: int, data: UserStateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, id)
    if not user:
        return send_error("Usuario no encontrado")
    user.state = data.state
    db.commit()
    return send_response(None, "Estado actualizado")
