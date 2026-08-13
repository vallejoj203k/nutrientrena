"""Tickets de soporte y comunicados de plataforma

El panel de plataforma tiene una sección de Soporte: la bandeja de tickets que
abren los coaches y los comunicados que Alzum publica dentro de la aplicación.
Ninguna de las dos cosas existía en la base de datos.

Tres tablas:

- support_tickets: el ticket en sí, con su cuenta de origen, prioridad y
  estado (abierto / en curso / resuelto).
- support_ticket_messages: el hilo. Sin conversación escrita, responder
  obligaría a salir a WhatsApp y no quedaría constancia de nada.
- platform_announcements: los comunicados, con su audiencia y su estado
  (borrador / publicado). Se guarda el CRITERIO de audiencia, no la lista de
  destinatarios, para que una cuenta que pase de prueba a activa reciba lo que
  le toca sin recalcular nada.

organization_id es opcional a propósito: un coach sin organización también
tiene derecho a pedir ayuda.

Revision ID: s0p1o2r3t4e5
Revises: ff5d6e7f8091
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa

revision = 's0p1o2r3t4e5'
down_revision = 'ff5d6e7f8091'
branch_labels = None
depends_on = None


def _tiene_tabla(nombre):
    bind = op.get_bind()
    return sa.inspect(bind).has_table(nombre)


def upgrade():
    if not _tiene_tabla('support_tickets'):
        op.create_table(
            'support_tickets',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('organization_id', sa.String(36),
                      sa.ForeignKey('organizations.id'), nullable=True),
            sa.Column('created_user_id', sa.Integer,
                      sa.ForeignKey('users.id'), nullable=False),
            sa.Column('subject', sa.String(255), nullable=False),
            sa.Column('body', sa.Text, nullable=True),
            sa.Column('priority', sa.String(10), nullable=False, server_default='media'),
            sa.Column('state', sa.String(15), nullable=False, server_default='abierto'),
            sa.Column('created_at', sa.DateTime, nullable=True),
            sa.Column('updated_at', sa.DateTime, nullable=True),
            sa.Column('resolved_at', sa.DateTime, nullable=True),
        )
        # La bandeja se ordena y filtra por estado casi siempre.
        op.create_index('ix_support_tickets_state', 'support_tickets', ['state'])
        op.create_index('ix_support_tickets_org', 'support_tickets', ['organization_id'])

    if not _tiene_tabla('support_ticket_messages'):
        op.create_table(
            'support_ticket_messages',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('ticket_id', sa.String(36),
                      sa.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False),
            sa.Column('author_user_id', sa.Integer,
                      sa.ForeignKey('users.id'), nullable=True),
            sa.Column('from_platform', sa.Integer, nullable=False, server_default='0'),
            sa.Column('body', sa.Text, nullable=False),
            sa.Column('created_at', sa.DateTime, nullable=True),
        )
        op.create_index('ix_support_messages_ticket', 'support_ticket_messages', ['ticket_id'])

    if not _tiene_tabla('platform_announcements'):
        op.create_table(
            'platform_announcements',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('body', sa.Text, nullable=True),
            sa.Column('audience', sa.String(15), nullable=False, server_default='todos'),
            sa.Column('state', sa.String(15), nullable=False, server_default='borrador'),
            sa.Column('created_user_id', sa.Integer,
                      sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=True),
            sa.Column('published_at', sa.DateTime, nullable=True),
        )


def downgrade():
    for tabla in ('support_ticket_messages', 'support_tickets', 'platform_announcements'):
        if _tiene_tabla(tabla):
            op.drop_table(tabla)
