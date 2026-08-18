from fastapi import Depends, Header, HTTPException, status
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
# Nivel 1 (plataforma), rol limitado: solo alimentos y ejercicios de la base
# maestra. Aparte a propósito de los grupos de abajo — no gestiona clientes,
# no ve organizaciones, no gestiona equipo — así que no se añade a
# STAFF_ROLES/COACH_UP/ADMIN_UP: hay que darle acceso explícito endpoint por
# endpoint, solo donde corresponde.
EDITOR_CONTENIDO_GLOBAL = 7
# Equipo interno de Alzum: atiende incidencias y consulta organizaciones y
# clientes para dar soporte, sin tocar facturación. Igual que el rol 7, se deja
# fuera de los grupos de abajo a propósito.
SOPORTE = 8

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


# Valor centinela de `X-Organization-Id` para "actúo como la plataforma y solo
# quiero SU catálogo". No es un id de organización porque no lo es: es la
# ausencia de organización, dicha explícitamente.
#
# Hace falta porque "todo" y "lo de la plataforma" no son lo mismo para un
# super-admin: sin cabecera ve la biblioteca entera —incluido lo privado de
# cada cuenta—, que es lo correcto cuando administra, y lo contrario de lo que
# espera quien entra por "Contenido global" a mantener el catálogo común.
SOLO_PLATAFORMA = "plataforma"


class OrgContext:
    """Resolved organization context for the current user."""
    def __init__(self, org_id: str | None, is_owner: bool, permissions: dict,
                 solo_plataforma: bool = False):
        self.org_id = org_id
        self.is_owner = is_owner
        self.permissions = permissions
        # True: se ve SOLO el catálogo de plataforma (organization_id NULL), no
        # lo privado de las cuentas. Nunca amplía lo que se ve, solo lo estrecha.
        self.solo_plataforma = solo_plataforma

    def can(self, key: str) -> bool:
        return bool(self.permissions.get(key, False))


def _contexto_natural(current_user, db: Session, roles: set[int]) -> OrgContext:
    """El contexto que le toca a alguien por lo que es, sin cambiar de sombrero.

    Para el contexto efectivo usar `get_org_context`, que además aplica la
    cabecera `X-Organization-Id`.

    - SUPERADMIN (Nivel 1, plataforma) → org_id=None, is_owner=True. Ve y
      controla todo: es el único bypass incondicional. Si quiere actuar dentro
      de una organización concreta lo pide explícitamente con la cabecera.
    - ADMIN dueño de una organización real (Nivel 2, "con su segundo
      sombrero") → org_id=<su organización>, is_owner=True. Actúa DENTRO de
      esa organización, no por encima de todas.
    - ADMIN o coach miembro de la organización de otro (Nivel 3, delegado)
      → org_id=<esa organización>, is_owner=False, permissions=<delegadas>.
      La membresía se busca en dos sitios porque hay dos pantallas distintas
      para añadir gente al equipo, que hasta ahora no se hablaban entre sí:
      "Coaches" (TeamMember, sin ninguna noción de organización hasta este
      cambio) y "Mi Organización" (OrganizationMember). Se mira primero
      TeamMember por ser la que de verdad se usa a diario.
    - ADMIN sin organización propia ni membresía: conserva el bypass total de
      antes (no hay organización en la que "meterlo"), para no romper cuentas
      de administración de plataforma que nunca pasaron por el modelo de
      organizaciones.
    - Coach: se resuelve exactamente igual (dueño / miembro / ninguno), salvo
      que sin organización ni membresía se queda SIN acceso especial en vez
      de con bypass — así era ya antes de este cambio.
    - Cliente / sin ficha: org_id=None, is_owner=False.

    Antes, cualquier ADMIN tenía bypass total sin mirar si en realidad era
    dueño de una organización (la migración que creó `organizations` le creó
    una a cada ADMIN/COACH existente). Eso hacía indistinguibles "Oswal como
    Alzum" y "Oswal como NutriEntrena": un ADMIN nunca actuaba dentro de su
    propia organización, siempre por encima de todas — lo contrario de lo que
    pide el documento de jerarquía.
    """
    from app.models.organization import Organization, OrganizationMember
    from app.models.team_member import TeamMember
    from app.models.user import UserDetail

    if SUPERADMIN in roles:
        return OrgContext(org_id=None, is_owner=True, permissions={})

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    if detail:
        org = db.query(Organization).filter(Organization.owner_id == detail.id).first()
        if org:
            return OrgContext(org_id=org.id, is_owner=True, permissions={})

        team_row = db.query(TeamMember).filter(
            TeamMember.user_detail_id == detail.id,
            TeamMember.organization_id.isnot(None),
        ).first()
        if team_row:
            return OrgContext(org_id=team_row.organization_id, is_owner=False, permissions={})

        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_detail_id == detail.id
        ).first()
        if membership:
            return OrgContext(
                org_id=membership.organization_id,
                is_owner=False,
                permissions=membership.permissions or {},
            )

    if ADMIN in roles:
        return OrgContext(org_id=None, is_owner=True, permissions={})
    return OrgContext(org_id=None, is_owner=False, permissions={})


def get_org_context(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    x_organization_id: str = Header(None, alias="X-Organization-Id"),
) -> OrgContext:
    """Contexto de organización de quien llama, con "segundo sombrero".

    Por defecto devuelve el contexto natural (ver `_contexto_natural`). La
    cabecera `X-Organization-Id` permite actuar explícitamente dentro de una
    organización concreta.

    Esto existe por el caso que dibuja el documento de jerarquía: la misma
    persona es super-admin de la plataforma Y dueña de NutriEntrena, dos
    sombreros. Sin esto, el super-admin se resolvía SIEMPRE como plataforma y
    no había manera de entrar en una organización concreta: mientras hubiera
    una sola organización daba igual, porque "toda la plataforma" y "esa
    organización" eran el mismo conjunto, pero con dos organizaciones los
    números divergen y no habría forma de ver la facturación de una sola ni de
    crear contenido privado para su equipo.

    Quién puede cambiar de sombrero:
    - Super-admin: a cualquier organización que exista.
    - Cualquier otro: solo a la suya, es decir, la cabecera únicamente puede
      confirmar el contexto que ya tenía. Si apunta a otra, 403 — si no, la
      cabecera sería una escalada de privilegios trivial.
    """
    roles = _user_role_ids(current_user.id, db)
    ctx = _contexto_natural(current_user, db, roles)

    # Llamado como función normal (los tests lo hacen), el valor por defecto es
    # el objeto Header, no None. Solo una cadena real cuenta como cabecera.
    if not isinstance(x_organization_id, str) or not x_organization_id.strip():
        return ctx

    destino = x_organization_id.strip()

    # "Solo la plataforma": lo pide quien ya está en contexto de plataforma
    # (super-admin, o admin sin organización propia). A cualquier otro no se le
    # ignora en silencio —se quedaría viendo lo suyo creyendo ver el catálogo
    # común—: se le dice que no.
    if destino == SOLO_PLATAFORMA:
        if ctx.org_id is None and ctx.is_owner:
            return OrgContext(org_id=None, is_owner=True, permissions={},
                              solo_plataforma=True)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No puedes actuar como la plataforma")

    if SUPERADMIN in roles:
        from app.models.organization import Organization

        org = db.query(Organization).filter(Organization.id == destino).first()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Organización no encontrada")
        return OrgContext(org_id=org.id, is_owner=True, permissions={})

    if destino != ctx.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No perteneces a esa organización")
    return ctx


def org_member_detail_ids(org_id: str, db: Session) -> set[str]:
    """UserDetail ids del equipo de una organización.

    Hay tres formas de pertenecer a una organización en este backend, y las
    tres cuentan: ser su dueño (Organization.owner_id), estar dado de alta en
    la pantalla "Coaches" (TeamMember) o en "Mi Organización"
    (OrganizationMember).
    """
    from app.models.organization import Organization, OrganizationMember
    from app.models.team_member import TeamMember

    ids: set[str] = set()

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org and org.owner_id:
        ids.add(org.owner_id)

    for row in db.query(TeamMember).filter(
        TeamMember.organization_id == org_id,
        TeamMember.user_detail_id.isnot(None),
    ).all():
        ids.add(row.user_detail_id)

    for row in db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id
    ).all():
        ids.add(row.user_detail_id)

    return ids


def org_client_detail_ids(org_id: str, db: Session) -> set[str]:
    """UserDetail ids de los clientes de una organización.

    Los clientes no cuelgan de la organización directamente: cuelgan de un
    coach (UserParent). Así que los de la organización son los asignados a
    cualquiera de su equipo.
    """
    from app.models.user import UserParent

    coach_ids = org_member_detail_ids(org_id, db)
    if not coach_ids:
        return set()

    rows = db.query(UserParent).filter(
        UserParent.parent_user_detail_id.in_(coach_ids)
    ).all()
    return {r.user_detail_id for r in rows}


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
