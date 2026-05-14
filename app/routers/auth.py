from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.menu import Menu, MenuRole
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, RecoverPasswordRequest, UserMeOut, MenuOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email, User.state == 1).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.put("/refresh-token", response_model=TokenResponse)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = db.query(User).filter(User.id == int(payload["sub"]), User.state == 1).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/recover-password")
def recover_password(data: RecoverPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"message": "Se ha enviado un correo con las instrucciones"}


@router.get("/me", response_model=UserMeOut)
def me(current_user: User = Depends(get_current_user)):
    return UserMeOut(
        id=current_user.id,
        name=current_user.name,
        last_name=current_user.last_name,
        email=current_user.email,
        photo=current_user.photo,
        role=current_user.role.name if current_user.role else None,
        slug=current_user.slug,
    )


@router.get("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Sesión cerrada"}


@router.get("/menus")
def menus(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.role_id:
        return []
    menu_roles = (
        db.query(MenuRole)
        .filter(MenuRole.role_id == current_user.role_id)
        .all()
    )
    menu_ids = [mr.menu_id for mr in menu_roles]
    menus = db.query(Menu).filter(Menu.menuId.in_(menu_ids)).all()
    return [MenuOut.model_validate(m) for m in menus]
