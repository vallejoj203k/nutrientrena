from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db

oauth2_scheme = HTTPBearer()

# ── Role ID constants (mirror app/models/role.py) ─────────────────────────────
SUPERADMIN = 1
ADMIN      = 2
SETTER     = 3
CLOSER     = 4
COACH      = 5
CLIENT     = 6

# ── Shorthand groups ──────────────────────────────────────────────────────────
STAFF_ROLES     = {SUPERADMIN, ADMIN, SETTER, CLOSER, COACH}   # any non-client
MANAGE_ROLES    = {SUPERADMIN, ADMIN}                           # can manage platform
COACH_UP        = {SUPERADMIN, ADMIN, COACH}                    # handle client data
ADMIN_UP        = {SUPERADMIN, ADMIN}                           # admin only


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
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


def _user_role_ids(user_id: int, db: Session) -> set[int]:
    """Return the set of role IDs for a given user."""
    from app.models.user import RoleUser
    rows = db.query(RoleUser).filter(RoleUser.user_id == user_id).all()
    return {r.role_id for r in rows}


def require_roles(*slugs: str):
    """Allow access if the user has at least one role matching the given slugs."""
    def checker(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
        from app.models.user import RoleUser
        from app.models.role import Role

        role_ids = [ru.role_id for ru in db.query(RoleUser).filter(RoleUser.user_id == current_user.id).all()]
        matched = db.query(Role).filter(Role.id.in_(role_ids), Role.slug.in_(slugs)).first()
        if not matched:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="No tienes permisos para esta acción")
        return current_user
    return checker


def require_role_ids(*role_ids: int):
    """Allow access if the user has at least one of the given role IDs."""
    allowed = set(role_ids)

    def checker(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
        user_roles = _user_role_ids(current_user.id, db)
        if not user_roles & allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="No tienes permisos para esta acción")
        return current_user
    return checker


def get_user_roles(current_user=Depends(get_current_user), db: Session = Depends(get_db)) -> set[int]:
    """Dependency that returns the set of role IDs for the current user."""
    return _user_role_ids(current_user.id, db)


def _get_coach_detail(user_id: int, db: Session):
    """Return the UserDetail for a coach/admin user."""
    from app.models.user import UserDetail
    return db.query(UserDetail).filter(UserDetail.user_id == user_id).first()


def _coach_client_ids(coach_detail_id: str, db: Session) -> set[str]:
    """Return the set of UserDetail IDs assigned to a given coach."""
    from app.models.user import UserParent
    rows = db.query(UserParent).filter(
        UserParent.parent_user_detail_id == coach_detail_id
    ).all()
    return {r.user_detail_id for r in rows}


def verify_client_access(client_detail_id: str, current_user, db: Session) -> None:
    """
    Raise 403 if current user is a coach who does NOT own the given client.
    Superadmins and admins always pass.
    """
    user_roles = _user_role_ids(current_user.id, db)
    if SUPERADMIN in user_roles or ADMIN in user_roles:
        return  # admins see everything

    if COACH not in user_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No tienes permisos para esta acción")

    coach_detail = _get_coach_detail(current_user.id, db)
    if not coach_detail:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Perfil de coach no encontrado")

    owned = _coach_client_ids(coach_detail.id, db)
    if client_detail_id not in owned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No tienes acceso a este cliente")


class OrgContext:
    """Resolved organization context for the current user."""
    def __init__(self, org_id: str | None, is_owner: bool, permissions: dict):
        self.org_id = org_id
        self.is_owner = is_owner
        self.permissions = permissions

    def can(self, key: str) -> bool:
        return bool(self.permissions.get(key, False))


def get_org_context(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrgContext:
    """
    Resolves the current user's organization context.
    - Platform SUPERADMIN/ADMIN → org_id=None, is_owner=True (bypass org restrictions)
    - Org owner (Nivel 2)       → org_id=<org>, is_owner=True
    - Org member (Nivel 3)      → org_id=<org>, is_owner=False, permissions=<delegated>
    - Client / other            → org_id=None, is_owner=False
    """
    from app.models.organization import Organization, OrganizationMember
    from app.models.user import UserDetail

    roles = _user_role_ids(current_user.id, db)
    if SUPERADMIN in roles or ADMIN in roles:
        return OrgContext(org_id=None, is_owner=True, permissions={})

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    if not detail:
        return OrgContext(org_id=None, is_owner=False, permissions={})

    org = db.query(Organization).filter(Organization.owner_id == detail.id).first()
    if org:
        return OrgContext(org_id=org.id, is_owner=True, permissions={})

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_detail_id == detail.id
    ).first()
    if membership:
        return OrgContext(
            org_id=membership.organization_id,
            is_owner=False,
            permissions=membership.permissions or {},
        )

    return OrgContext(org_id=None, is_owner=False, permissions={})


def filter_clients_by_role(all_clients: list, current_user, db: Session) -> list:
    """
    If the current user is a coach, return only their assigned clients.
    Admins and superadmins get all clients unchanged.
    """
    user_roles = _user_role_ids(current_user.id, db)
    if SUPERADMIN in user_roles or ADMIN in user_roles:
        return all_clients

    if COACH in user_roles:
        coach_detail = _get_coach_detail(current_user.id, db)
        if not coach_detail:
            return []
        owned = _coach_client_ids(coach_detail.id, db)
        return [c for c in all_clients if c.id in owned]

    return []
