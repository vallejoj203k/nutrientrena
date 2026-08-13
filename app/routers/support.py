"""Soporte: tickets de los coaches y comunicados de la plataforma.

El fichero tiene dos mitades, y la separación importa:

- `/support/*` es lo que usa un COACH: abrir un ticket, ver los suyos,
  responder, y leer los comunicados publicados que le tocan.
- `/admin/support/*` es la bandeja de Alzum: todos los tickets de todas las
  cuentas, cambiar su estado, y escribir y publicar comunicados.

Se construyen las dos a la vez a propósito. Una bandeja de entrada sin forma de
que entre nada es una pantalla que siempre está vacía y que parece rota; y un
comunicado que no se ve en ninguna parte no es un comunicado.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import (
    SUPERADMIN, SOPORTE, _user_role_ids, get_current_user, get_org_context, OrgContext,
)
from app.core.responses import send_error, send_response
from app.database import get_db
from app.models.organization import Organization
from app.models.support import (
    AUDIENCIAS, ESTADOS_COMUNICADO, ESTADOS_TICKET, PRIORIDADES,
    PlatformAnnouncement, SupportTicket, SupportTicketMessage,
)
from app.models.user import User, UserDetail

router = APIRouter(prefix="/support", tags=["Soporte"])
router_admin = APIRouter(prefix="/admin/support", tags=["Soporte"])


def _es_equipo_alzum(current_user, db: Session) -> bool:
    roles = _user_role_ids(current_user.id, db)
    return SUPERADMIN in roles or SOPORTE in roles


def _nombre(user_id: Optional[int], db: Session) -> Optional[str]:
    if not user_id:
        return None
    d = db.query(UserDetail).filter(UserDetail.user_id == user_id).first()
    if d:
        return f"{d.name} {d.last_name or ''}".strip()
    u = db.query(User).filter(User.id == user_id).first()
    return u.email if u else None


def _serializar(t: SupportTicket, db: Session, nombres_org: dict, con_hilo=False) -> dict:
    fila = {
        "id": t.id,
        "subject": t.subject,
        "body": t.body,
        "priority": t.priority or "media",
        "state": t.state or "abierto",
        "organization_id": t.organization_id,
        "organization_name": nombres_org.get(t.organization_id),
        "autor": _nombre(t.created_user_id, db),
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "respuestas": len(t.messages),
    }
    if con_hilo:
        fila["mensajes"] = [{
            "id": m.id,
            "body": m.body,
            "de_plataforma": bool(m.from_platform),
            "autor": _nombre(m.author_user_id, db),
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in t.messages]
    return fila


def _totales(consulta) -> dict:
    """Los tres contadores del prototipo. Se calculan sobre la misma consulta
    que la lista, para que no digan una cosa distinta de lo que se ve."""
    filas = consulta.all()
    return {
        "abiertos": sum(1 for t in filas if (t.state or "abierto") == "abierto"),
        "en_curso": sum(1 for t in filas if t.state == "en_curso"),
        "resueltos": sum(1 for t in filas if t.state == "resuelto"),
        "total": len(filas),
    }


# ── Lado del coach ──────────────────────────────────────────────────────────

class NuevoTicket(BaseModel):
    subject: str
    body: Optional[str] = None
    priority: str = "media"


class NuevaRespuesta(BaseModel):
    body: str


@router.get("/tickets", summary="Mis tickets de soporte",
            description="Los tickets abiertos desde mi cuenta.")
def mis_tickets(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    org: OrgContext = Depends(get_org_context),
):
    consulta = db.query(SupportTicket)
    if org.org_id:
        # Todo el equipo de la cuenta ve los tickets de la cuenta: si solo los
        # viera quien los abrió, un coach de vacaciones dejaría a su equipo sin
        # poder seguir la incidencia.
        consulta = consulta.filter(SupportTicket.organization_id == org.org_id)
    else:
        consulta = consulta.filter(SupportTicket.created_user_id == current_user.id)

    nombres_org = {o.id: o.name for o in db.query(Organization).all()}
    filas = consulta.order_by(SupportTicket.created_at.desc()).all()
    return send_response([_serializar(t, db, nombres_org) for t in filas], "OK")


@router.post("/tickets", summary="Abrir un ticket de soporte")
def abrir_ticket(
    data: NuevoTicket,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    org: OrgContext = Depends(get_org_context),
):
    asunto = (data.subject or "").strip()
    if not asunto:
        return send_error("Escribe de qué va la incidencia", code=400)
    prioridad = data.priority if data.priority in PRIORIDADES else "media"

    t = SupportTicket(
        organization_id=org.org_id,
        created_user_id=current_user.id,
        subject=asunto,
        body=(data.body or "").strip() or None,
        priority=prioridad,
        state="abierto",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    nombres_org = {o.id: o.name for o in db.query(Organization).all()}
    return send_response(_serializar(t, db, nombres_org), "Ticket creado")


@router.get("/tickets/{ticket_id}", summary="Ver un ticket con su conversación")
def ver_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    org: OrgContext = Depends(get_org_context),
):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        return send_error("Ticket no encontrado", code=404)
    if not _puede_ver(t, current_user, org, db):
        return send_error("Este ticket no es tuyo", code=403)
    nombres_org = {o.id: o.name for o in db.query(Organization).all()}
    return send_response(_serializar(t, db, nombres_org, con_hilo=True), "OK")


@router.post("/tickets/{ticket_id}/messages", summary="Responder en un ticket")
def responder(
    ticket_id: str,
    data: NuevaRespuesta,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    org: OrgContext = Depends(get_org_context),
):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        return send_error("Ticket no encontrado", code=404)

    equipo = _es_equipo_alzum(current_user, db)
    if not equipo and not _puede_ver(t, current_user, org, db):
        return send_error("Este ticket no es tuyo", code=403)

    texto = (data.body or "").strip()
    if not texto:
        return send_error("El mensaje está vacío", code=400)

    db.add(SupportTicketMessage(
        ticket_id=t.id, author_user_id=current_user.id,
        from_platform=1 if equipo else 0, body=texto,
    ))
    # Que Alzum conteste pasa el ticket a "en curso" solo: si hubiera que
    # acordarse de moverlo a mano, la bandeja mentiría a los dos días.
    if equipo and (t.state or "abierto") == "abierto":
        t.state = "en_curso"
    t.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
    nombres_org = {o.id: o.name for o in db.query(Organization).all()}
    return send_response(_serializar(t, db, nombres_org, con_hilo=True), "Respuesta enviada")


def _puede_ver(t: SupportTicket, current_user, org: OrgContext, db: Session) -> bool:
    if _es_equipo_alzum(current_user, db):
        return True
    if t.created_user_id == current_user.id:
        return True
    return bool(t.organization_id) and t.organization_id == org.org_id


@router.get("/announcements", summary="Comunicados publicados que me tocan",
            description="Los avisos de la plataforma para mi cuenta. Solo publicados.")
def mis_comunicados(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    org: OrgContext = Depends(get_org_context),
):
    """La audiencia se resuelve AQUÍ, en el momento de leer.

    Se guarda el criterio ("activos") y no la lista de destinatarios, así que
    una cuenta que pase de prueba a activa empieza a recibir lo que le toca sin
    que nadie recalcule nada.
    """
    estado = None
    if org.org_id:
        o = db.query(Organization).filter(Organization.id == org.org_id).first()
        estado = (o.state or "activa") if o else None

    filas = db.query(PlatformAnnouncement).filter(
        PlatformAnnouncement.state == "publicado"
    ).order_by(PlatformAnnouncement.published_at.desc()).all()

    def toca(a):
        if a.audience == "todos":
            return True
        if a.audience == "activos":
            return estado == "activa"
        if a.audience == "prueba":
            return estado == "prueba"
        return False

    return send_response([{
        "id": a.id, "title": a.title, "body": a.body,
        "published_at": a.published_at.isoformat() if a.published_at else None,
    } for a in filas if toca(a)], "OK")


# ── Bandeja de Alzum ────────────────────────────────────────────────────────

def _exige_soporte(current_user, db: Session):
    from app.routers.admin_panel import _exige_seccion
    return _exige_seccion(current_user, db, "soporte")


class CambioEstadoTicket(BaseModel):
    state: str


class Comunicado(BaseModel):
    title: str
    body: Optional[str] = None
    audience: str = "todos"


@router_admin.get("/tickets", summary="Bandeja de tickets de la plataforma")
def bandeja(
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_soporte(current_user, db)
    if motivo:
        return send_error(motivo, code=403)

    nombres_org = {o.id: o.name for o in db.query(Organization).all()}
    todos = db.query(SupportTicket)
    totales = _totales(todos)

    consulta = db.query(SupportTicket)
    if estado in ESTADOS_TICKET:
        consulta = consulta.filter(SupportTicket.state == estado)
    filas = consulta.order_by(SupportTicket.created_at.desc()).all()

    return send_response({
        "tickets": [_serializar(t, db, nombres_org) for t in filas],
        "totales": totales,
    }, "OK")


@router_admin.get("/tickets/{ticket_id}", summary="Ver un ticket con su conversación")
def ver_como_alzum(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_soporte(current_user, db)
    if motivo:
        return send_error(motivo, code=403)
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        return send_error("Ticket no encontrado", code=404)
    nombres_org = {o.id: o.name for o in db.query(Organization).all()}
    return send_response(_serializar(t, db, nombres_org, con_hilo=True), "OK")


@router_admin.put("/tickets/{ticket_id}/state", summary="Cambiar el estado de un ticket")
def cambiar_estado_ticket(
    ticket_id: str,
    data: CambioEstadoTicket,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_soporte(current_user, db)
    if motivo:
        return send_error(motivo, code=403)
    if data.state not in ESTADOS_TICKET:
        return send_error(f"Estado no válido. Admitidos: {', '.join(ESTADOS_TICKET)}", code=400)

    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        return send_error("Ticket no encontrado", code=404)

    t.state = data.state
    t.resolved_at = datetime.utcnow() if data.state == "resuelto" else None
    t.updated_at = datetime.utcnow()
    db.commit()
    nombres_org = {o.id: o.name for o in db.query(Organization).all()}
    return send_response(_serializar(t, db, nombres_org), "Estado actualizado")


# ── Comunicados ─────────────────────────────────────────────────────────────

def _serializar_comunicado(a: PlatformAnnouncement) -> dict:
    return {
        "id": a.id, "title": a.title, "body": a.body,
        "audience": a.audience or "todos", "state": a.state or "borrador",
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "published_at": a.published_at.isoformat() if a.published_at else None,
    }


@router_admin.get("/announcements", summary="Comunicados de la plataforma")
def listar_comunicados(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_soporte(current_user, db)
    if motivo:
        return send_error(motivo, code=403)
    filas = db.query(PlatformAnnouncement).order_by(
        PlatformAnnouncement.created_at.desc()).all()
    return send_response([_serializar_comunicado(a) for a in filas], "OK")


@router_admin.post("/announcements", summary="Escribir un comunicado")
def crear_comunicado(
    data: Comunicado,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_soporte(current_user, db)
    if motivo:
        return send_error(motivo, code=403)
    titulo = (data.title or "").strip()
    if not titulo:
        return send_error("El comunicado necesita un título", code=400)
    if data.audience not in AUDIENCIAS:
        return send_error(f"Audiencia no válida. Admitidas: {', '.join(AUDIENCIAS)}", code=400)

    # Nace en borrador SIEMPRE. Publicar es un acto aparte: escribir un aviso a
    # todas las cuentas y que salga solo por darle a guardar da demasiado miedo
    # como para usar la pantalla con calma.
    a = PlatformAnnouncement(
        title=titulo, body=(data.body or "").strip() or None,
        audience=data.audience, state="borrador",
        created_user_id=current_user.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return send_response(_serializar_comunicado(a), "Comunicado guardado en borrador")


@router_admin.put("/announcements/{anuncio_id}", summary="Editar un comunicado")
def editar_comunicado(
    anuncio_id: str,
    data: Comunicado,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_soporte(current_user, db)
    if motivo:
        return send_error(motivo, code=403)
    a = db.query(PlatformAnnouncement).filter(PlatformAnnouncement.id == anuncio_id).first()
    if not a:
        return send_error("Comunicado no encontrado", code=404)
    titulo = (data.title or "").strip()
    if not titulo:
        return send_error("El comunicado necesita un título", code=400)
    if data.audience not in AUDIENCIAS:
        return send_error(f"Audiencia no válida. Admitidas: {', '.join(AUDIENCIAS)}", code=400)

    a.title = titulo
    a.body = (data.body or "").strip() or None
    a.audience = data.audience
    db.commit()
    return send_response(_serializar_comunicado(a), "Comunicado actualizado")


@router_admin.put("/announcements/{anuncio_id}/state", summary="Publicar o despublicar")
def publicar(
    anuncio_id: str,
    data: CambioEstadoTicket,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_soporte(current_user, db)
    if motivo:
        return send_error(motivo, code=403)
    if data.state not in ESTADOS_COMUNICADO:
        return send_error(f"Estado no válido. Admitidos: {', '.join(ESTADOS_COMUNICADO)}", code=400)

    a = db.query(PlatformAnnouncement).filter(PlatformAnnouncement.id == anuncio_id).first()
    if not a:
        return send_error("Comunicado no encontrado", code=404)

    a.state = data.state
    # Despublicar conserva la fecha original: si se vuelve a publicar, no debe
    # colarse arriba del todo como si fuera nuevo.
    if data.state == "publicado" and not a.published_at:
        a.published_at = datetime.utcnow()
    db.commit()
    return send_response(_serializar_comunicado(a),
                         "Comunicado publicado" if data.state == "publicado" else "Comunicado retirado")


@router_admin.delete("/announcements/{anuncio_id}", summary="Eliminar un comunicado")
def borrar_comunicado(
    anuncio_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = _exige_soporte(current_user, db)
    if motivo:
        return send_error(motivo, code=403)
    a = db.query(PlatformAnnouncement).filter(PlatformAnnouncement.id == anuncio_id).first()
    if not a:
        return send_error("Comunicado no encontrado", code=404)
    db.delete(a)
    db.commit()
    return send_response(None, "Comunicado eliminado")
