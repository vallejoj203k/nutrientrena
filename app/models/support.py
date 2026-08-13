"""Soporte: tickets de los coaches y comunicados de la plataforma.

Dos cosas distintas que comparten pantalla:

- Un **ticket** lo abre un coach cuando algo no le funciona. Va de uno a uno:
  su cuenta pregunta, Alzum responde. Lleva conversación, porque un ticket sin
  respuesta escrita obliga a contestar por WhatsApp y entonces no queda nada.
- Un **comunicado** va de Alzum a todos: un aviso de mantenimiento, una
  novedad. No es una conversación, y por eso vive en su propia tabla en vez de
  ser "un ticket sin remitente".

Los estados son los del prototipo, y son deliberadamente pocos: abierto, en
curso, resuelto. Un flujo con diez estados no lo mantiene nadie.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

ESTADOS_TICKET = ("abierto", "en_curso", "resuelto")
PRIORIDADES = ("alta", "media", "baja")
# A quién se le enseña un comunicado. Se guarda el criterio, no la lista de
# destinatarios: si mañana una cuenta pasa de prueba a activa, el comunicado
# dirigido a "activos" tiene que alcanzarla sin recalcular nada.
AUDIENCIAS = ("todos", "activos", "prueba")
ESTADOS_COMUNICADO = ("borrador", "publicado")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # De qué cuenta viene. Puede ser NULL: un coach sin organización también
    # tiene derecho a pedir ayuda.
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    created_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    priority = Column(String(10), nullable=False, default="media", server_default="media")
    state = Column(String(15), nullable=False, default="abierto", server_default="abierto")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    messages = relationship(
        "SupportTicketMessage", back_populates="ticket",
        cascade="all, delete-orphan", order_by="SupportTicketMessage.created_at",
    )


class SupportTicketMessage(Base):
    """Cada respuesta del hilo, del coach o de Alzum.

    `from_platform` se guarda en la fila en vez de deducirse del rol del autor:
    los roles cambian con el tiempo y el histórico tiene que seguir diciendo
    quién hablaba desde qué lado cuando lo escribió.
    """
    __tablename__ = "support_ticket_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    from_platform = Column(Integer, nullable=False, default=0, server_default="0")
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("SupportTicket", back_populates="messages")


class PlatformAnnouncement(Base):
    __tablename__ = "platform_announcements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    audience = Column(String(15), nullable=False, default="todos", server_default="todos")
    state = Column(String(15), nullable=False, default="borrador", server_default="borrador")
    created_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
