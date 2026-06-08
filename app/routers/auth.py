from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token, hash_password
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.core.email import send_recover_password_email
from app.models.user import User, UserDetail, RoleUser
from app.models.menu import Menu, MenuRole
from app.schemas.auth import LoginRequest, RefreshTokenRequest, RecoverPasswordRequest, ResetPasswordRequest, MenuOut
from app.schemas.user import UserDetailOut

router = APIRouter(prefix="/auth", tags=["Auth"])

# Status ID that means disabled (from ParametersSeeder: "Inactivo" is index 2 of "Estado de Usuarios")
STATUS_INACTIVE = 2


def _build_menu_tree(menu_list: list) -> list:
    result = []
    for menu in menu_list:
        if menu.menuParentId is None:
            children = [m for m in menu_list if m.menuParentId == menu.menuId]
            entry = MenuOut.model_validate(menu)
            entry.childMenu = [MenuOut.model_validate(c) for c in children]
            result.append(entry)
    return result


@router.post("/login", summary="Iniciar sesión", description="Autentica con email y contraseña. Retorna tokens JWT de acceso y refresco.")
@limiter.limit("10/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password):
        return send_error("Usuario y contraseña incorrectos.", {"error": "Unauthorised"}, code=401)

    user_detail = db.query(UserDetail).filter(UserDetail.user_id == user.id).first()
    if user_detail and user_detail.status_id == STATUS_INACTIVE:
        return send_error("Usuario esta deshabilitado", {"error": "Unauthorised"}, code=401)

    role_user = db.query(RoleUser).filter(RoleUser.user_id == user.id).first()

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return send_response(
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "role_id": role_user.role_id if role_user else None,
            },
            "token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        },
        "User login successfully.",
    )


@router.put("/refresh-token", summary="Renovar tokens", description="Genera un nuevo par de tokens de acceso y refresco usando el refresh token.")
def refresh_token_endpoint(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        return send_error("Token inválido", code=401)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        return send_error("Usuario no encontrado", code=401)
    access_token = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    return send_response(
        {"token": access_token, "refresh_token": new_refresh, "token_type": "Bearer"},
        "User login successfully.",
    )


@router.post("/recover-password", summary="Solicitar recuperación de contraseña", description="Envía un email con enlace para resetear la contraseña. Respuesta genérica para no revelar si el email existe.")
@limiter.limit("5/minute")
def recover_password(request: Request, data: RecoverPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # Respuesta genérica para no revelar si el email existe
        return send_response([], "Se envio un correo electronico.")

    user_detail = db.query(UserDetail).filter(UserDetail.user_id == user.id).first()
    name = user_detail.name if user_detail else user.name

    reset_token = create_access_token({"sub": str(user.id), "purpose": "reset"})
    send_recover_password_email(to=user.email, name=name, token=reset_token)

    return send_response([], "Se envio un correo electronico.")


@router.post("/reset-password", summary="Restablecer contraseña", description="Cambia la contraseña del usuario usando el token recibido por email.")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.token)
    if payload is None:
        return send_error("El enlace ha expirado o no es válido", code=400)
    if payload.get("type") != "access" or payload.get("purpose") != "reset":
        return send_error("Token inválido", code=400)

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        return send_error("Usuario no encontrado", code=404)

    if len(data.password) < 6:
        return send_error("La contraseña debe tener al menos 6 caracteres", code=400)

    user.password = hash_password(data.password)
    db.commit()
    return send_response(None, "Contraseña actualizada correctamente")


@router.get("/me", summary="Perfil del usuario autenticado", description="Retorna el perfil completo y roles del usuario autenticado.")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    if not user_detail:
        return send_error("Perfil no encontrado")

    role_users = db.query(RoleUser).filter(RoleUser.user_id == current_user.id).all()
    roles = [{"id": ru.role_id, "name": ru.role.name if ru.role else None} for ru in role_users]

    data = UserDetailOut.model_validate(user_detail).model_dump()
    data["email"] = current_user.email
    data["roles"] = roles
    return send_response(data, "Successfully.")


@router.get("/logout", summary="Cerrar sesión", description="Invalida la sesión del usuario autenticado.")
def logout(current_user: User = Depends(get_current_user)):
    return send_response([], "Successfully logged out.")


@router.get("/menus", summary="Menús del usuario", description="Retorna el árbol de menús accesibles según los roles del usuario autenticado.")
def menus(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        role_users = db.query(RoleUser).filter(RoleUser.user_id == current_user.id).all()
        role_ids = [ru.role_id for ru in role_users]

        menu_roles = db.query(MenuRole).filter(MenuRole.role_id.in_(role_ids)).all()
        menu_ids = list({mr.menu_id for mr in menu_roles})

        menu_list = db.query(Menu).filter(Menu.menuId.in_(menu_ids)).all()
        tree = _build_menu_tree(menu_list)

        return send_response([m.model_dump() for m in tree], "List Menus by User")
    except Exception:
        return send_error("Hubo un error.")
