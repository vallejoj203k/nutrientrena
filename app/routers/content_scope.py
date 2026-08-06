"""Mover contenido entre una organización y el catálogo de plataforma.

El documento de jerarquía lo pide explícitamente: el super-admin ve el
contenido de todas las organizaciones y "promueve lo bueno a Plataforma". Ver
sí podía; promover no existía en ningún sitio.

Promover es poner organization_id a NULL: a partir de ahí el contenido lo ven
todas las organizaciones como base de partida. La organización de origen NO lo
pierde de vista —el contenido de plataforma es visible para todos—, lo que
pierde es la exclusividad, que es justamente el sentido de promoverlo.

La operación es reversible: el mismo endpoint admite devolverlo a una
organización, porque una promoción hecha por error sin vuelta atrás sería una
trampa.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import (
    require_role_ids, get_org_context, OrgContext, SUPERADMIN, ADMIN,
)
from app.core.responses import send_response, send_error
from app.models.organization import Organization
from app.models.routine import Routine
from app.models.training import Training
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.diet import Diet

router = APIRouter(prefix="/content", tags=["Content scope"])

# Los cuatro tipos de contenido que tienen organización.
TIPOS = {
    "routine": (Routine, "rutina"),
    "diet": (Diet, "dieta"),
    "aliment": (Aliment, "alimento"),
    "training": (Training, "ejercicio"),
}


class CambioDeAlcance(BaseModel):
    # None = catálogo de plataforma. Se distingue de "no enviado" con un
    # centinela, porque aquí null es un valor con significado propio.
    organization_id: Optional[str] = None


@router.put(
    "/{tipo}/{id}/organization",
    summary="Mover contenido entre organización y plataforma",
    description=(
        "Con organization_id null, promueve el contenido al catálogo de "
        "plataforma para que lo vean todas las organizaciones. Con un id, lo "
        "devuelve a esa organización. Solo la administración de plataforma."
    ),
)
def cambiar_alcance(
    tipo: str,
    id: str,
    data: CambioDeAlcance,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN)),
    org: OrgContext = Depends(get_org_context),
):
    entrada = TIPOS.get(tipo)
    if not entrada:
        return send_error(
            f"Tipo no válido. Admitidos: {', '.join(sorted(TIPOS))}", code=400
        )
    modelo, etiqueta = entrada

    # Solo quien está por encima de las organizaciones. Un dueño de
    # organización no puede regalar su contenido al resto de la plataforma ni,
    # mucho menos, mover el de otra.
    if not (org.org_id is None and org.is_owner):
        return send_error(
            "Solo la administración de plataforma puede mover contenido entre "
            "organizaciones", code=403,
        )

    # Los ids son int en unos modelos y uuid en otros.
    columna = modelo.id
    valor = id
    if columna.type.python_type is int:
        try:
            valor = int(id)
        except (TypeError, ValueError):
            return send_error(f"No se encontró {etiqueta} con id {id}", code=404)

    obj = db.query(modelo).filter(columna == valor).first()
    if not obj:
        return send_error(f"No se encontró {etiqueta} con id {id}", code=404)

    destino = data.organization_id
    if destino is not None:
        if not db.query(Organization).filter(Organization.id == destino).first():
            return send_error("Organización no encontrada", code=404)

    anterior = obj.organization_id
    if anterior == destino:
        return send_error(
            f"Este {etiqueta} ya está donde pides" if destino
            else f"Este {etiqueta} ya es del catálogo de plataforma",
            code=400,
        )

    obj.organization_id = destino
    db.commit()
    db.refresh(obj)

    return send_response(
        {"id": str(obj.id), "tipo": tipo,
         "organization_id": obj.organization_id,
         "organization_id_anterior": anterior},
        f"{etiqueta.capitalize()} promovido al catálogo de plataforma" if destino is None
        else f"{etiqueta.capitalize()} movido a la organización",
    )
