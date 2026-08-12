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
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import (
    get_current_user, _user_role_ids,
    SUPERADMIN, ADMIN, EDITOR_CONTENIDO_GLOBAL, SOPORTE,
)
from app.core.responses import send_response, send_error
from app.models.organization import Organization
from app.models.user import UserDetail

router = APIRouter(prefix="/admin", tags=["Admin panel"])

# Las diez secciones del panel, en el orden del documento.
SECCIONES = [
    {"id": "vision",       "nombre": "Visión general",        "icono": "chart"},
    {"id": "organizaciones", "nombre": "Coaches / Organizaciones", "icono": "users"},
    {"id": "clientes",     "nombre": "Clientes finales",      "icono": "user"},
    {"id": "facturacion",  "nombre": "Facturación e ingresos", "icono": "card"},
    {"id": "planes",       "nombre": "Planes y suscripciones", "icono": "box"},
    {"id": "contenido",    "nombre": "Contenido global",      "icono": "shield"},
    {"id": "soporte",      "nombre": "Soporte",               "icono": "life"},
    {"id": "analiticas",   "nombre": "Analíticas",            "icono": "trend"},
    {"id": "equipo",       "nombre": "Equipo de Alzum",       "icono": "team"},
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
