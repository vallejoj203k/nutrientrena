from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from slugify import slugify

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreateRequest, UserUpdateRequest, UserStateRequest, UserAssignRequest, WeeksTrainingRequest, UserOut

router = APIRouter(prefix="/users", tags=["Users"])


def _get_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.post("")
def create(data: UserCreateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

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
    return UserOut.model_validate(user)


@router.post("/assign")
def assigned(data: UserAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, data.user_id)
    user.instructor_id = data.instructor_id
    db.commit()
    return {"message": "Asignado correctamente"}


@router.post("/weeks")
def weeks_training(data: WeeksTrainingRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, data.user_id)
    user.notes = str(data.weeks)
    db.commit()
    return {"message": "Semanas actualizadas"}


@router.get("/{slug}/findAll")
def find_all(slug: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    instructor = db.query(User).filter(User.slug == slug).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor no encontrado")
    clients = db.query(User).filter(User.instructor_id == instructor.id).all()
    return [UserOut.model_validate(c) for c in clients]


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
        raise HTTPException(status_code=404, detail="Instructor no encontrado")

    q = db.query(User).filter(User.instructor_id == instructor.id)
    if search:
        q = q.filter(
            (User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    total = q.count()
    users = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "data": [UserOut.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "per_page": per_page,
        "last_page": (total + per_page - 1) // per_page,
    }


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return UserOut.model_validate(_get_or_404(db, id))


@router.put("/{id}/update")
def updated(id: int, data: UserUpdateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.put("/{id}/change")
def change_state(id: int, data: UserStateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = _get_or_404(db, id)
    user.state = data.state
    db.commit()
    return {"message": "Estado actualizado"}


@router.get("/report")
def report_users(db: Session = Depends(get_db), _=Depends(get_current_user)):
    total = db.query(User).count()
    active = db.query(User).filter(User.state == 1).count()
    return {"total": total, "active": active, "inactive": total - active}
