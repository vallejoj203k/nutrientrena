"""Facturación por organización.

El documento de jerarquía pide que el dueño de una organización vea la
facturación de SU organización, que el super-admin vea la global, y que los
coaches del equipo no vean facturación en absoluto.

Los datos económicos ya existían por cliente (UserDetail.precio,
estado_pago, importe_pagado, importe_pendiente, metodo_pago), editables desde
la ficha del cliente, pero no había ninguna vista agregada: nadie podía ver
cuánto factura una organización sin abrir cliente por cliente. Esto lo agrega,
ya scoped por organización.

No es una pasarela de pago ni un sistema de facturas: no se emiten documentos
ni se cobra nada. Es la lectura agregada de lo que ya se registra a mano.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import (
    require_role_ids, get_org_context, OrgContext,
    org_client_detail_ids, org_member_detail_ids,
    _coach_client_ids, SUPERADMIN, ADMIN,
)
from app.core.responses import send_response, send_error
from app.models.role import CLIENT
from app.models.user import UserDetail, RoleUser

router = APIRouter(prefix="/billing", tags=["Billing"])


def _clientes_visibles(org: OrgContext, db: Session):
    """Los clientes cuya facturación puede ver quien llama, o None si no puede.

    - Super-admin (y admin sin organización propia): toda la plataforma.
    - Dueño de organización: los clientes de su organización.
    - Cualquier otro (coach del equipo, delegado no dueño): nada. La
      facturación es del nivel 2 hacia arriba.
    """
    if org.org_id is None and org.is_owner:
        client_user_ids = [r.user_id for r in db.query(RoleUser).filter(RoleUser.role_id == CLIENT).all()]
        return db.query(UserDetail).filter(UserDetail.user_id.in_(client_user_ids)).all()

    if org.org_id and org.is_owner:
        detail_ids = org_client_detail_ids(org.org_id, db)
        if not detail_ids:
            return []
        return db.query(UserDetail).filter(UserDetail.id.in_(detail_ids)).all()

    return None


def _totales(clientes) -> dict:
    facturado = sum(c.precio or 0 for c in clientes)
    cobrado = sum(c.importe_pagado or 0 for c in clientes)
    # importe_pendiente se rellena a mano y puede quedar desfasado; si falta,
    # se deduce de lo facturado menos lo cobrado.
    pendiente = sum(
        c.importe_pendiente if c.importe_pendiente is not None else max((c.precio or 0) - (c.importe_pagado or 0), 0)
        for c in clientes
    )

    por_estado: dict[str, dict] = {}
    for c in clientes:
        estado = (c.estado_pago or "sin estado").lower()
        acc = por_estado.setdefault(estado, {"estado": estado, "clientes": 0, "facturado": 0.0})
        acc["clientes"] += 1
        acc["facturado"] += c.precio or 0

    return {
        "total_facturado": round(facturado, 2),
        "total_cobrado": round(cobrado, 2),
        "total_pendiente": round(pendiente, 2),
        "clientes_totales": len(clientes),
        "clientes_de_pago": sum(1 for c in clientes if (c.precio or 0) > 0),
        "por_estado": sorted(
            ({**v, "facturado": round(v["facturado"], 2)} for v in por_estado.values()),
            key=lambda x: -x["facturado"],
        ),
    }


@router.get("/summary", summary="Resumen de facturación", description="Totales facturado/cobrado/pendiente de la organización, o de toda la plataforma si es super-admin.")
def summary(
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN)),
    org: OrgContext = Depends(get_org_context),
):
    clientes = _clientes_visibles(org, db)
    if clientes is None:
        return send_error("No tienes acceso a la facturación", code=403)

    return send_response({
        **_totales(clientes),
        "alcance": "plataforma" if org.org_id is None else "organizacion",
        "organization_id": org.org_id,
    }, "ok")


@router.get("/by-coach", summary="Facturación por coach", description="Desglose de lo facturado por cada coach del equipo.")
def by_coach(
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN)),
    org: OrgContext = Depends(get_org_context),
):
    clientes = _clientes_visibles(org, db)
    if clientes is None:
        return send_error("No tienes acceso a la facturación", code=403)

    if org.org_id:
        coach_ids = org_member_detail_ids(org.org_id, db)
    else:
        # Plataforma entera: cualquiera que tenga clientes asignados.
        from app.models.user import UserParent
        coach_ids = {r.parent_user_detail_id for r in db.query(UserParent.parent_user_detail_id).distinct().all()}

    visibles = {c.id for c in clientes}
    por_id = {c.id: c for c in clientes}

    resultado = []
    for coach in db.query(UserDetail).filter(UserDetail.id.in_(coach_ids)).all() if coach_ids else []:
        suyos = [por_id[cid] for cid in _coach_client_ids(coach.id, db) & visibles]
        if not suyos:
            continue
        t = _totales(suyos)
        resultado.append({
            "coach_user_detail_id": coach.id,
            "coach_name": getattr(coach, "name", None),
            "clientes": t["clientes_totales"],
            "facturado": t["total_facturado"],
            "cobrado": t["total_cobrado"],
            "pendiente": t["total_pendiente"],
        })

    resultado.sort(key=lambda x: -x["facturado"])
    return send_response(resultado, "ok")


@router.get("/clients", summary="Facturación por cliente", description="Detalle de cobro de cada cliente dentro del alcance permitido.")
def clients(
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN)),
    org: OrgContext = Depends(get_org_context),
):
    clientes = _clientes_visibles(org, db)
    if clientes is None:
        return send_error("No tienes acceso a la facturación", code=403)

    return send_response([
        {
            "user_detail_id": c.id,
            "name": getattr(c, "name", None),
            "precio": c.precio,
            "estado_pago": c.estado_pago,
            "importe_pagado": c.importe_pagado,
            "importe_pendiente": c.importe_pendiente,
            "metodo_pago": c.metodo_pago,
        }
        for c in sorted(clientes, key=lambda x: -(x.precio or 0))
    ], "ok")
