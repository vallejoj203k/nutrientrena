from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.models.user import User
from app.models.menu import Menu, MenuRole
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, RecoverPasswordRequest, UserMeOut, MenuOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email, User.state == 1).first()
    if not user or not verify_password(data.password, user.password):
        return send_error("Credenciales incorrectas", code=401)
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return send_response(
        {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"},
        "Login exitoso",
    )


@router.put("/refresh-token")
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        return send_error("Token inválido", code=401)
    user = db.query(User).filter(User.id == int(payload["sub"]), User.state == 1).first()
    if not user:
        return send_error("Usuario no encontrado", code=401)
    access_token = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    return send_response(
        {"access_token": access_token, "refresh_token": new_refresh, "token_type": "bearer"},
        "Token renovado",
    )


@router.post("/recover-password")
def recover_password(data: RecoverPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return send_error("Usuario no encontrado")
    return send_response(None, "Se ha enviado un correo con las instrucciones")


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    data = UserMeOut(
        id=current_user.id,
        name=current_user.name,
        last_name=current_user.last_name,
        email=current_user.email,
        photo=current_user.photo,
        role=current_user.role.name if current_user.role else None,
        slug=current_user.slug,
    )
    return send_response(data.model_dump(), "OK")


@router.get("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return send_response(None, "Sesión cerrada")


@router.get("/menus")
def menus(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.role_id:
        return send_response([], "OK")
    menu_roles = db.query(MenuRole).filter(MenuRole.role_id == current_user.role_id).all()
    menu_ids = [mr.menu_id for mr in menu_roles]
    items = db.query(Menu).filter(Menu.menuId.in_(menu_ids)).all()
    return send_response([MenuOut.model_validate(m).model_dump() for m in items], "OK")
