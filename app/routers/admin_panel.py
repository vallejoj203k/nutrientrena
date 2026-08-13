"""Panel de administración de la plataforma.

El documento del panel de admin lo describe como una aplicación SEPARADA del
panel de coach —"no son la misma pantalla con un botón"— con su propio espacio
en /admin y su propia navegación.

Este módulo solo resuelve el esqueleto: quién puede entrar y qué secciones ve
cada quien. El contenido de cada sección llega en los sprints siguientes.

Las secciones se sirven desde el backend, no se escriben en el HTML, por dos
razones: que el menú de un rol no dependa de que alguien acierte a copiarlo en
cada página, y que se pueda probar sin navegador.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import (
    get_current_user, _user_role_ids,
    SUPERADMIN, ADMIN, EDITOR_CONTENIDO_GLOBAL, SOPORTE, COACH, CLIENT,
)
from app.core.responses import send_response, send_error
from app.core.security import hash_password
from app.models.organization import Organization, OrganizationMember
from app.models.role import Role
from app.models.user import User, UserDetail, RoleUser, UserParent

router = APIRouter(prefix="/admin", tags=["Admin panel"])

# Las diez secciones del panel, en el orden del documento.
SECCIONES = [
    {"id": "vision",       "nombre": "Visión general",        "icono": "chart"},
    {"id": "organizaciones", "nombre": "Coaches",                   "icono": "users"},
    {"id": "clientes",     "nombre": "Clientes finales",      "icono": "user"},
    {"id": "facturacion",  "nombre": "Facturación",           "icono": "card"},
    {"id": "planes",       "nombre": "Planes y suscripciones", "icono": "box"},
    {"id": "contenido",    "nombre": "Contenido global",      "icono": "shield"},
    {"id": "soporte",      "nombre": "Soporte",               "icono": "life"},
    {"id": "analiticas",   "nombre": "Analíticas",            "icono": "trend"},
    {"id": "equipo",       "nombre": "Equipo Alzum",          "icono": "team"},
    {"id": "configuracion", "nombre": "Configuración",        "icono": "gear"},
]

# Qué ve cada rol del equipo de Alzum. Lista de lo PERMITIDO, no de lo
# prohibido: una sección nueva no se le abre a nadie por descuido.
#
# "Finanzas" aparece en el documento marcado como futuro, así que no se crea
# todavía: un rol que nadie puede asignar solo añade ruido.
ACCESO = {
    SUPERADMIN: [s["id"] for s in SECCIONES],          # todo
    EDITOR_CONTENIDO_GLOBAL: ["contenido"],
    SOPORTE: ["soporte", "organizaciones", "clientes"],
}


def secciones_de(roles: set) -> list:
    """Secciones visibles para un conjunto de roles, en el orden del documento."""
    permitidas = set()
    for rol, ids in ACCESO.items():
        if rol in roles:
            permitidas.update(ids)
    return [s for s in SECCIONES if s["id"] in permitidas]


@router.get("/me", summary="Contexto del panel de administración",
            description="Si el usuario puede entrar al panel de plataforma y qué secciones ve.")
def admin_me(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = _user_role_ids(current_user.id, db)
    secciones = secciones_de(roles)

    if not secciones:
        # Un coach o un cliente no tienen nada que hacer aquí. Se responde 403
        # y no una lista vacía: "no puedes entrar" y "puedes entrar pero no hay
        # nada" son cosas distintas y el frontend debe distinguirlas.
        return send_error("No tienes acceso al panel de plataforma", code=403)

    detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()

    # Organizaciones a las que puede cambiarse desde el selector de contexto.
    # Solo el super-admin trabaja como cualquier organización; el resto del
    # equipo interno no tiene panel de coach al que saltar.
    organizaciones = []
    if SUPERADMIN in roles or ADMIN in roles:
        organizaciones = [
            {"id": o.id, "name": o.name}
            for o in db.query(Organization).order_by(Organization.name).all()
        ]

    return send_response({
        "nombre": (detail.name if detail else None) or current_user.email,
        "secciones": secciones,
        "organizaciones": organizaciones,
        "es_superadmin": SUPERADMIN in roles,
    }, "OK")


# ── Cuentas (organizaciones) ────────────────────────────────────────────────

ESTADOS = ["activa", "prueba", "impago", "suspendida"]


class NuevaCuenta(BaseModel):
    name: str
    country: Optional[str] = None
    state: str = "activa"
    # Dueño: o se apunta a un usuario que ya existe, o se crea en el mismo paso.
    owner_user_detail_id: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_password: Optional[str] = None


class CambioEstado(BaseModel):
    state: str


def _exige_seccion(current_user, db: Session, seccion: str):
    """Devuelve el motivo por el que no puede usar esta sección, o None."""
    roles = _user_role_ids(current_user.id, db)
    if seccion not in [s["id"] for s in secciones_de(roles)]:
        return "No tienes acceso a esta sección del panel"
    return None


def _es_superadmin(current_user, db: Session) -> bool:
    return SUPERADMIN in _user_role_ids(current_user.id, db)


def _detalles_de_equipo(org_id: str, db: Session) -> set:
    """UserDetail ids del equipo de una organización (dueño incluido)."""
    from app.core.dependencies import org_member_detail_ids
    return org_member_detail_ids(org_id, db)


def _clientes_de(org_id: str, db: Session) -> int:
    from app.core.dependencies import org_client_detail_ids
    return len(org_client_detail_ids(org_id, db))


def _serializar_cuenta(org: Organization, db: Session) -> dict:
    dueno = db.query(UserDetail).filter(UserDetail.id == org.owner_id).first()
    email = None
    if dueno and dueno.user_id:
        u = db.query(User).filter(User.id == dueno.user_id).first()
        email = u.email if u else None
    return {
        "id": org.id,
        "name": org.name,
        "state": org.state or "activa",
        "country": org.country,
        "owner_name": (f"{dueno.name} {dueno.last_name or ''}".strip() if dueno else None),
        "owner_email": email,
        "owner_user_detail_id": org.owner_id,
        "coaches": len(_detalles_de_equipo(org.id, db)),
        "clientes": _clientes_de(org.id, db),
        "created_at": org.created_at.isoformat() if org.created_at else None,
        # Plan e importe dependen de la pasarela de pago, que está fuera de
        # alcance. Se devuelven en null a propósito en vez de inventarlos: la
        # pantalla los enseña como "—" y así no parece que ya funcionen.
        "plan": None,
        "mrr": None,
    }


@router.get("/organizations", summary="Cuentas de la plataforma",
            description="Todas las organizaciones con su dueño, equipo, clientes y estado.")
def listar_cuentas(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_seccion(current_user, db, "organizaciones")
    if motivo:
        return send_error(motivo, code=403)

    orgs = db.query(Organization).order_by(Organization.name).all()
    cuentas = [_serializar_cuenta(o, db) for o in orgs]
    return send_response({
        "cuentas": cuentas,
        "totales": {
            "cuentas": len(cuentas),
            "clientes": sum(c["clientes"] for c in cuentas),
            "por_estado": {e: sum(1 for c in cuentas if c["state"] == e) for e in ESTADOS},
        },
    }, "OK")


@router.post("/organizations", summary="Dar de alta una cuenta",
             description="Crea una organización y le asigna un dueño, existente o nuevo.")
def crear_cuenta(
    data: NuevaCuenta,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Dar de alta cuentas es cosa del super-admin. Soporte las ve, no las crea.
    if not _es_superadmin(current_user, db):
        return send_error("Solo el super-admin puede dar de alta cuentas", code=403)

    if not (data.name or "").strip():
        return send_error("El nombre de la cuenta es obligatorio", code=400)
    if data.state not in ESTADOS:
        return send_error(f"Estado no válido. Admitidos: {', '.join(ESTADOS)}", code=400)

    # ── Resolver el dueño
    if data.owner_user_detail_id:
        dueno = db.query(UserDetail).filter(UserDetail.id == data.owner_user_detail_id).first()
        if not dueno:
            return send_error("El usuario indicado como dueño no existe", code=404)
        ya = db.query(Organization).filter(Organization.owner_id == dueno.id).first()
        if ya:
            return send_error(f"Esa persona ya dirige la cuenta «{ya.name}»", code=400)
    else:
        # Crear la cuenta del entrenador en el mismo paso. Antes esto no se
        # podía: POST /organizations fijaba el dueño como quien llamaba, así
        # que no había forma de dar de alta un centro para otra persona.
        if not (data.owner_name and data.owner_email and data.owner_password):
            return send_error(
                "Para crear el dueño hacen falta nombre, correo y contraseña", code=400)
        if len(data.owner_password) < 6:
            return send_error("La contraseña debe tener al menos 6 caracteres", code=400)
        if db.query(User).filter(User.email == data.owner_email).first():
            return send_error("Ese correo ya está registrado", code=400)

        partes = data.owner_name.strip().split(" ")
        user = User(name=partes[0], email=data.owner_email,
                    password=hash_password(data.owner_password))
        db.add(user)
        db.flush()
        db.add(RoleUser(role_id=COACH, user_id=user.id))
        dueno = UserDetail(
            user_id=user.id,
            name=partes[0],
            last_name=" ".join(partes[1:]) or None,
        )
        db.add(dueno)
        db.flush()

    slug = f"{data.name.lower().replace(' ', '-')[:40]}-{str(uuid.uuid4())[:8]}"
    org = Organization(
        id=str(uuid.uuid4()),
        name=data.name.strip(),
        slug=slug,
        owner_id=dueno.id,
        country=(data.country or None),
        state=data.state,
        is_active=(data.state != "suspendida"),
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return send_response(_serializar_cuenta(org, db), "Cuenta creada")


@router.put("/organizations/{org_id}/state", summary="Cambiar el estado de una cuenta",
            description="Activa, prueba, impago o suspendida.")
def cambiar_estado(
    org_id: str,
    data: CambioEstado,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not _es_superadmin(current_user, db):
        return send_error("Solo el super-admin puede cambiar el estado de una cuenta", code=403)
    if data.state not in ESTADOS:
        return send_error(f"Estado no válido. Admitidos: {', '.join(ESTADOS)}", code=400)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return send_error("Cuenta no encontrada", code=404)

    org.state = data.state
    # is_active se mantiene en sincronía: hay código del panel de coach que lo
    # consulta y no debe quedarse desfasado.
    org.is_active = (data.state != "suspendida")
    db.commit()
    db.refresh(org)
    return send_response(_serializar_cuenta(org, db), "Estado actualizado")


@router.get("/coaches-sin-cuenta", summary="Entrenadores sin organización",
            description="Coaches que no dirigen ni pertenecen a ninguna cuenta.")
def coaches_sin_cuenta(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Red de seguridad.

    Un coach sin organización crea contenido con organization_id NULL, y eso
    lo publica en el catálogo de plataforma: lo ve TODA organización. Es la
    fuga que abría dar de alta un entrenador sin cuenta, así que conviene
    poder verlos y arreglarlos.
    """
    motivo = _exige_seccion(current_user, db, "organizaciones")
    if motivo:
        return send_error(motivo, code=403)

    ids_coach = {r.user_id for r in db.query(RoleUser).filter(RoleUser.role_id == COACH).all()}
    if not ids_coach:
        return send_response([], "OK")

    con_cuenta = {o.owner_id for o in db.query(Organization).all()}
    con_cuenta |= {m.user_detail_id for m in db.query(OrganizationMember).all()}
    from app.models.team_member import TeamMember
    con_cuenta |= {t.user_detail_id for t in db.query(TeamMember).filter(
        TeamMember.organization_id.isnot(None), TeamMember.user_detail_id.isnot(None)).all()}

    sueltos = []
    for d in db.query(UserDetail).filter(UserDetail.user_id.in_(ids_coach)).all():
        if d.id in con_cuenta:
            continue
        u = db.query(User).filter(User.id == d.user_id).first()
        sueltos.append({
            "user_detail_id": d.id,
            "name": f"{d.name} {d.last_name or ''}".strip(),
            "email": u.email if u else None,
        })
    return send_response(sueltos, "OK")


@router.get("/organizations/{org_id}", summary="Ficha de una cuenta",
            description="Datos de la organización, su equipo y sus clientes.")
def ficha_cuenta(
    org_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_seccion(current_user, db, "organizaciones")
    if motivo:
        return send_error(motivo, code=403)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return send_error("Cuenta no encontrada", code=404)

    ficha = _serializar_cuenta(org, db)

    # Equipo: quién trabaja en esa cuenta y cuántos clientes lleva cada uno.
    from app.core.dependencies import org_member_detail_ids, _coach_client_ids
    equipo = []
    for d in db.query(UserDetail).filter(UserDetail.id.in_(org_member_detail_ids(org.id, db))).all():
        u = db.query(User).filter(User.id == d.user_id).first()
        equipo.append({
            "user_detail_id": d.id,
            "name": f"{d.name} {d.last_name or ''}".strip(),
            "email": u.email if u else None,
            "es_duenio": d.id == org.owner_id,
            "clientes": len(_coach_client_ids(d.id, db)),
        })
    equipo.sort(key=lambda x: (not x["es_duenio"], x["name"] or ""))
    ficha["equipo"] = equipo
    return send_response(ficha, "OK")


# ── Clientes finales ────────────────────────────────────────────────────────

# Los cuatro estados del ciclo de vida que ya usa el panel de coach
# (UserDetail.lifecycle_status). El panel de plataforma los LEE, no los toca.
LIFECYCLE = {"activo": "Activo", "pendiente": "Pendiente",
             "pausado": "Pausado", "finalizado": "Finalizado"}


def _ultima_actividad(detail_ids: set, user_ids: set, db: Session) -> dict:
    """Fecha de la última señal de vida de cada cliente, por user_detail_id.

    Se mira lo que el cliente HACE, no lo que el coach le pone: entrenamientos
    registrados, check-ins enviados y días de progreso. Sin `last_login` en el
    modelo, esto es lo más cercano que hay a "última actividad" sin inventarla.

    Se consulta en tres barridos, no uno por cliente: con unos cientos de
    clientes la versión ingenua serían cientos de consultas por pintar la
    tabla.
    """
    from sqlalchemy import func

    from app.models.checkin import WeeklyCheckin
    from app.models.progress_day import ProgressDay
    from app.models.session_log import WorkoutSession

    ultima = {}

    def anotar(detail_id, fecha):
        if not fecha:
            return
        previa = ultima.get(detail_id)
        if previa is None or fecha > previa:
            ultima[detail_id] = fecha

    if detail_ids:
        for did, f in db.query(
            WorkoutSession.client_user_detail_id, func.max(WorkoutSession.session_date)
        ).filter(WorkoutSession.client_user_detail_id.in_(detail_ids)).group_by(
                WorkoutSession.client_user_detail_id).all():
            anotar(did, f)

        for did, f in db.query(
            WeeklyCheckin.client_user_detail_id, func.max(WeeklyCheckin.checkin_date)
        ).filter(WeeklyCheckin.client_user_detail_id.in_(detail_ids)).group_by(
                WeeklyCheckin.client_user_detail_id).all():
            anotar(did, f)

    # ProgressDay cuelga de users.id, no de user_details.id.
    if user_ids:
        por_user = {}
        for uid, f in db.query(
            ProgressDay.user_id, func.max(ProgressDay.date)
        ).filter(ProgressDay.user_id.in_(user_ids)).group_by(ProgressDay.user_id).all():
            por_user[uid] = f
        if por_user:
            for d in db.query(UserDetail).filter(UserDetail.user_id.in_(list(por_user))).all():
                anotar(d.id, por_user.get(d.user_id))

    return ultima


@router.get("/clients", summary="Clientes finales de la plataforma",
            description="Los clientes de todos los coaches, en solo lectura, para dar soporte.")
def listar_clientes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Vista de solo lectura, y deliberadamente pobre en datos.

    Un cliente final no es cliente de Alzum: es cliente de su coach. Aquí se
    devuelve lo justo para dar soporte —quién es, de qué cuenta, en qué estado
    y si sigue vivo— y nada de lo íntimo: ni peso, ni medidas, ni fotos, ni
    patologías. No es un olvido; es la línea que separa dar soporte de leer el
    historial médico de alguien que no te lo ha dado a ti.

    Por eso tampoco hay endpoints de edición: desde el panel de plataforma no
    se modifica el cliente de nadie. Para eso está "Entrar como".
    """
    motivo = _exige_seccion(current_user, db, "clientes")
    if motivo:
        return send_error(motivo, code=403)

    from app.core.dependencies import org_member_detail_ids

    # A qué cuenta pertenece cada coach, y cómo se llama esa cuenta.
    orgs = db.query(Organization).order_by(Organization.name).all()
    cuenta_de_coach, nombre_cuenta = {}, {}
    for o in orgs:
        nombre_cuenta[o.id] = o.name
        for did in org_member_detail_ids(o.id, db):
            cuenta_de_coach[did] = o.id

    # Los clientes cuelgan de un coach (UserParent), no de la organización.
    vinculos = db.query(UserParent).all()
    coach_de_cliente = {v.user_detail_id: v.parent_user_detail_id for v in vinculos}
    if not coach_de_cliente:
        return send_response({"clientes": [], "cuentas": [
            {"id": o.id, "name": o.name} for o in orgs], "totales": {
            "total": 0, "activos": 0, "finalizados": 0}}, "OK")

    detalles = db.query(UserDetail).filter(
        UserDetail.id.in_(list(coach_de_cliente)),
        UserDetail.deleted_at.is_(None),
    ).all()

    coaches = {d.id: d for d in db.query(UserDetail).filter(
        UserDetail.id.in_(set(coach_de_cliente.values()))).all()}
    correos = {u.id: u.email for u in db.query(User).filter(
        User.id.in_([d.user_id for d in detalles if d.user_id])).all()}

    actividad = _ultima_actividad(
        {d.id for d in detalles},
        {d.user_id for d in detalles if d.user_id},
        db,
    )

    clientes = []
    for d in detalles:
        coach_id = coach_de_cliente.get(d.id)
        coach = coaches.get(coach_id)
        org_id = cuenta_de_coach.get(coach_id)
        act = actividad.get(d.id)
        clientes.append({
            "user_detail_id": d.id,
            "name": f"{d.name} {d.last_name or ''}".strip(),
            "email": correos.get(d.user_id),
            # El coach que lo lleva y la cuenta a la que pertenece son cosas
            # distintas: en un equipo, varios coaches comparten cuenta.
            "coach_name": (f"{coach.name} {coach.last_name or ''}".strip() if coach else None),
            "organization_id": org_id,
            # Un coach sin organización no tiene cuenta a la que atribuirlo.
            # Se dice, en vez de colgarlo de una cualquiera.
            "organization_name": nombre_cuenta.get(org_id),
            "state": d.lifecycle_status or "activo",
            # "Alta" es cuando entró en la plataforma, no cuando empieza su
            # programa: start_date se queda vacío en muchas fichas.
            "created_at": (d.created_at or d.start_date).isoformat() if (d.created_at or d.start_date) else None,
            "last_activity": act.isoformat() if act else None,
        })
    clientes.sort(key=lambda c: (c["name"] or "").lower())

    return send_response({
        "clientes": clientes,
        # Para el desplegable "Todas las cuentas": solo las que tienen clientes,
        # más una entrada para los coaches sueltos si los hay.
        "cuentas": [{"id": o.id, "name": o.name} for o in orgs],
        "totales": {
            "total": len(clientes),
            "activos": sum(1 for c in clientes if c["state"] == "activo"),
            "finalizados": sum(1 for c in clientes if c["state"] == "finalizado"),
        },
    }, "OK")


# ── Contenido global ────────────────────────────────────────────────────────

# Los tipos que se pueden listar desde el panel, y cómo se lee cada uno.
#
# Dos familias distintas, y la diferencia importa:
#
# - Con `organizacion=True`: la tabla tiene organization_id, así que existe
#   contenido "de plataforma" (NULL) y contenido privado de una cuenta. Es lo
#   que se puede promover.
# - Con `organizacion=False`: catálogos que no tienen dueño porque son la
#   fuente única de verdad de la plataforma —grupos musculares, tipos de dieta,
#   grupos de alimentos—. Todo lo que hay ahí ya es global por definición.
def _catalogo_contenido():
    from app.models.muscle_group import MuscleGroup
    from app.models.nutrition.aliment import Aliment
    from app.models.nutrition.diet import Diet
    from app.models.nutrition.group_food import GroupFood
    from app.models.nutrition.type_food import TypeFood
    from app.models.routine import Routine
    from app.models.training import Training

    return {
        "routines":     {"modelo": Routine,    "campo": "name",  "familia": "entrenamiento", "organizacion": True,  "etiqueta": "Rutinas",              "promover": "routine"},
        "trainings":    {"modelo": Training,   "campo": "name",  "familia": "entrenamiento", "organizacion": True,  "etiqueta": "Ejercicios",           "promover": "training"},
        "muscle_groups": {"modelo": MuscleGroup, "campo": "name", "familia": "entrenamiento", "organizacion": False, "etiqueta": "Grupos musculares",   "promover": None},
        "diets":        {"modelo": Diet,       "campo": "title", "familia": "nutricion",     "organizacion": True,  "etiqueta": "Dietas",               "promover": "diet"},
        "aliments":     {"modelo": Aliment,    "campo": "name",  "familia": "nutricion",     "organizacion": True,  "etiqueta": "Alimentos",            "promover": "aliment"},
        "type_foods":   {"modelo": TypeFood,   "campo": "name",  "familia": "nutricion",     "organizacion": False, "etiqueta": "Tipos de dieta",       "promover": None},
        "group_foods":  {"modelo": GroupFood,  "campo": "name",  "familia": "nutricion",     "organizacion": False, "etiqueta": "Grupos de alimentos",  "promover": None},
    }


# El catálogo de alimentos puede tener miles de filas (la importación del
# USDA). Se lista un tramo y se dice cuántos hay: una tabla que se corta en
# silencio parece completa y no lo está.
TOPE_CONTENIDO = 200


def _fila_contenido(tipo: str, obj, cfg: dict, db: Session, nombres_org: dict) -> dict:
    nombre = getattr(obj, cfg["campo"], None)
    org_id = getattr(obj, "organization_id", None) if cfg["organizacion"] else None
    fila = {
        "id": str(obj.id),
        "tipo": tipo,
        "nombre": nombre,
        "organization_id": org_id,
        "organization_name": nombres_org.get(org_id) if org_id else None,
        "origen": "plataforma" if org_id is None else "organizacion",
        "created_at": obj.created_at.isoformat() if getattr(obj, "created_at", None) else None,
    }
    # Las columnas que enseña el prototipo para cada tipo. Se rellenan solo si
    # el modelo las tiene: el resto de tipos no las gasta.
    if tipo == "routines":
        nivel = getattr(obj, "training_level", None)
        fila.update({
            "objetivo": obj.objective,
            # ParameterDetail guarda el texto en `description`, no en `name`.
            "nivel": getattr(nivel, "description", None),
            "dias": obj.days,
            # `time` es la duración del programa en semanas.
            "duracion": f"{obj.time} semanas" if obj.time else None,
        })
    elif tipo == "trainings":
        grupo = getattr(obj, "muscle_group", None)
        fila.update({"grupo": getattr(grupo, "name", None), "material": obj.material})
    elif tipo == "diets":
        fila.update({"calorias": obj.calories, "tipo_dieta": getattr(getattr(obj, "type", None), "name", None)})
    elif tipo == "aliments":
        fila.update({"calorias": obj.calories, "grupo": getattr(getattr(obj, "group_food", None), "name", None)})
    elif not cfg["organizacion"]:
        # Los catálogos sin dueño solo tienen nombre y descripción, y se editan
        # desde el propio panel.
        fila["descripcion"] = getattr(obj, "description", None)
    return fila


@router.get("/content", summary="Contenido global de la plataforma",
            description="El catálogo de fábrica que ven todas las cuentas, y el contenido privado de cada una.")
def listar_contenido(
    tipo: str = "routines",
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """La base común de Alzum: lo que toda cuenta nueva encuentra ya hecho.

    Se devuelven siempre los conteos de todos los tipos —los necesita la
    navegación por pestañas— y las filas solo del tipo pedido.
    """
    motivo = _exige_seccion(current_user, db, "contenido")
    if motivo:
        return send_error(motivo, code=403)

    catalogo = _catalogo_contenido()

    def base(cfg, solo=None):
        c = db.query(cfg["modelo"])
        if cfg["organizacion"] and solo == "plataforma":
            c = c.filter(cfg["modelo"].organization_id.is_(None))
        elif cfg["organizacion"] and solo == "organizacion":
            c = c.filter(cfg["modelo"].organization_id.isnot(None))
        return c

    conteos = {
        t: {"global": base(cfg, "plataforma").count(),
            "cuentas": base(cfg, "organizacion").count() if cfg["organizacion"] else 0,
            "etiqueta": cfg["etiqueta"], "familia": cfg["familia"],
            "organizacion": cfg["organizacion"]}
        for t, cfg in catalogo.items()
    }
    totales = {
        "global": sum(c["global"] for c in conteos.values()),
        "cuentas": sum(c["cuentas"] for c in conteos.values()),
        # El circuito de propuestas del prototipo (un coach propone, la
        # plataforma aprueba) todavía no existe: no hay ni tabla ni forma de
        # proponer. Se devuelve null en vez de 0 para que la pantalla lo
        # muestre como pendiente y no como "no hay ninguna".
        "propuestas": None,
    }

    nombres_org = {o.id: o.name for o in db.query(Organization).all()}

    # "organizaciones" no es un tipo: es todo el contenido privado de las
    # cuentas, de los cuatro tipos que tienen organización. Es la lista desde
    # la que se promueve.
    if tipo == "organizaciones":
        filas, total = [], 0
        for t, cfg in catalogo.items():
            if not cfg["organizacion"]:
                continue
            consulta = base(cfg, "organizacion")
            if q:
                consulta = consulta.filter(getattr(cfg["modelo"], cfg["campo"]).ilike(f"%{q}%"))
            total += consulta.count()
            for obj in consulta.limit(TOPE_CONTENIDO).all():
                filas.append(_fila_contenido(t, obj, cfg, db, nombres_org))
        filas.sort(key=lambda r: (r["organization_name"] or "", r["nombre"] or ""))
        return send_response({
            "tipo": tipo, "conteos": conteos, "totales": totales,
            "items": filas[:TOPE_CONTENIDO], "total": total,
            "recortado": total > len(filas[:TOPE_CONTENIDO]),
        }, "OK")

    cfg = catalogo.get(tipo)
    if not cfg:
        return send_error(f"Tipo no válido. Admitidos: {', '.join(sorted(catalogo))}, organizaciones", code=400)

    consulta = base(cfg, "plataforma")
    if q:
        consulta = consulta.filter(getattr(cfg["modelo"], cfg["campo"]).ilike(f"%{q}%"))
    total = consulta.count()
    objetos = consulta.order_by(getattr(cfg["modelo"], cfg["campo"])).limit(TOPE_CONTENIDO).all()

    return send_response({
        "tipo": tipo, "conteos": conteos, "totales": totales,
        "items": [_fila_contenido(tipo, o, cfg, db, nombres_org) for o in objetos],
        "total": total, "recortado": total > len(objetos),
        "promover": cfg["promover"],
    }, "OK")


class CatalogoItem(BaseModel):
    name: str
    description: Optional[str] = None


# Los tres catálogos que el prototipo llama "la fuente única de verdad": no
# tienen organización, así que se editan aquí y en ningún otro sitio.
CATALOGOS_EDITABLES = {"muscle_groups", "type_foods", "group_foods"}


def _modelo_catalogo(tipo: str):
    cfg = _catalogo_contenido().get(tipo)
    return cfg["modelo"] if cfg and tipo in CATALOGOS_EDITABLES else None


@router.post("/content/{tipo}", summary="Crear una entrada de catálogo global")
def crear_catalogo(
    tipo: str,
    data: CatalogoItem,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_seccion(current_user, db, "contenido")
    if motivo:
        return send_error(motivo, code=403)
    modelo = _modelo_catalogo(tipo)
    if not modelo:
        return send_error(
            "Solo se crean desde aquí los catálogos de plataforma: "
            f"{', '.join(sorted(CATALOGOS_EDITABLES))}", code=400)

    nombre = (data.name or "").strip()
    if not nombre:
        return send_error("El nombre es obligatorio", code=400)
    if db.query(modelo).filter(modelo.name == nombre).first():
        return send_error("Ya existe una entrada con ese nombre", code=400)

    obj = modelo(name=nombre, description=(data.description or None))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response({"id": obj.id, "name": obj.name}, "Creado")


@router.put("/content/{tipo}/{id}", summary="Renombrar una entrada de catálogo global")
def editar_catalogo(
    tipo: str,
    id: int,
    data: CatalogoItem,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_seccion(current_user, db, "contenido")
    if motivo:
        return send_error(motivo, code=403)
    modelo = _modelo_catalogo(tipo)
    if not modelo:
        return send_error("Ese tipo no se edita desde aquí", code=400)

    obj = db.query(modelo).filter(modelo.id == id).first()
    if not obj:
        return send_error("No encontrado", code=404)

    nombre = (data.name or "").strip()
    if not nombre:
        return send_error("El nombre es obligatorio", code=400)
    if db.query(modelo).filter(modelo.name == nombre, modelo.id != id).first():
        return send_error("Ya existe una entrada con ese nombre", code=400)

    obj.name = nombre
    if data.description is not None:
        obj.description = data.description or None
    db.commit()
    return send_response({"id": obj.id, "name": obj.name}, "Actualizado")


@router.delete("/content/{tipo}/{id}", summary="Borrar una entrada de catálogo global")
def borrar_catalogo(
    tipo: str,
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Se niega si algo lo está usando.

    Estos catálogos son la base de toda la plataforma: borrar un grupo muscular
    que usan trescientos ejercicios de cuatro cuentas distintas no es
    "limpiar", es romperle la librería a gente que no se ha enterado.
    """
    motivo = _exige_seccion(current_user, db, "contenido")
    if motivo:
        return send_error(motivo, code=403)
    modelo = _modelo_catalogo(tipo)
    if not modelo:
        return send_error("Ese tipo no se borra desde aquí", code=400)

    obj = db.query(modelo).filter(modelo.id == id).first()
    if not obj:
        return send_error("No encontrado", code=404)

    from app.models.nutrition.aliment import Aliment
    from app.models.nutrition.diet import Diet
    from app.models.training import Training

    usos = 0
    if tipo == "muscle_groups":
        usos = db.query(Training).filter(Training.muscle_group_id == id).count()
    elif tipo == "type_foods":
        usos = db.query(Diet).filter(Diet.type_id == id).count()
    elif tipo == "group_foods":
        usos = db.query(Aliment).filter(Aliment.group_food_id == id).count()
    if usos:
        return send_error(
            f"No se puede borrar: lo están usando {usos} elemento(s). "
            "Cámbialos primero o renombra esta entrada.", code=400)

    db.delete(obj)
    db.commit()
    return send_response(None, "Borrado")


@router.get("/roles", summary="Roles del equipo de Alzum",
            description="Los roles internos y qué secciones ve cada uno. Para previsualizar el panel.")
def roles_del_equipo(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Alimenta el selector "ver el panel como".

    Sirve para comprobar qué ve cada miembro del equipo sin tener que crear una
    cuenta y entrar con ella. Solo el super-admin: es una herramienta de
    verificación, no una forma de saltarse permisos —previsualizar cambia lo
    que se PINTA, no lo que la API deja hacer.
    """
    if not _es_superadmin(current_user, db):
        return send_error("Solo el super-admin puede previsualizar el panel", code=403)

    nombres = {r.id: r.name for r in db.query(Role).filter(Role.id.in_(list(ACCESO))).all()}
    return send_response([
        {"role_id": rid,
         "nombre": nombres.get(rid, f"Rol {rid}"),
         "secciones": [s["id"] for s in secciones_de({rid})]}
        for rid in ACCESO
    ], "OK")
