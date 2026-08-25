import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(20), nullable=False)  # 'individual' | 'group'
    name = Column(String(255), nullable=True)
    # Un grupo se define de dos maneras distintas, y conviene no mezclarlas:
    #
    #   · por REGLA (audience): "mis clientes", "mis coaches". La lista se
    #     resuelve cada vez, así que quien entra en la cuenta entra en el grupo
    #     y quien se va, sale. Es lo que se espera de "todos mis clientes".
    #   · a mano (audience NULL): la lista de personas que se eligió al crearlo
    #     y no cambia sola, como un grupo de WhatsApp.
    audience = Column(String(30), nullable=True)
    # Difusión: solo escribe quien lo creó, y los demás responden en privado.
    # Sin esto, "un mensaje a todos mis clientes" pone a hablar entre sí a
    # gente que no se conoce y que no eligió estar junta.
    broadcast = Column(Boolean, nullable=False, default=False, server_default="0")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by_user_id])
    participants = relationship("ChatParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_read_at = Column(DateTime, nullable=True)  # última vez que el usuario abrió esta conversación

    conversation = relationship("ChatConversation", back_populates="participants")
    user = relationship("User", foreign_keys=[user_id])


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Un mensaje puede ser SOLO un archivo, sin texto: obligar a escribir algo
    # para poder mandar una foto es pedir relleno.
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Adjuntos: la foto de la comida, el PDF de la dieta. Se guarda el nombre
    # original porque "a3f9…-2b1c.pdf" no le dice nada a nadie, y el tamaño
    # para poder avisar antes de que alguien se descargue 8 MB con datos.
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    attachment_type = Column(String(100), nullable=True)
    attachment_size = Column(Integer, nullable=True)

    conversation = relationship("ChatConversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_user_id])
