from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_roles(*slugs: str):
    """Check that the current user has at least one role matching the given slugs."""
    def checker(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
        from app.models.user import RoleUser
        from app.models.role import Role

        role_users = db.query(RoleUser).filter(RoleUser.user_id == current_user.id).all()
        role_ids = [ru.role_id for ru in role_users]
        matched = db.query(Role).filter(Role.id.in_(role_ids), Role.slug.in_(slugs)).first()
        if not matched:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción",
            )
        return current_user

    return checker
