import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Date, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    password = Column(String(255), nullable=False)
    remember_token = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    detail = relationship("UserDetail", back_populates="user", uselist=False,
                          foreign_keys="UserDetail.user_id")
    role_users = relationship("RoleUser", back_populates="user")
    client_target = relationship("ClientTarget", back_populates="user", uselist=False)
    events = relationship("EventUser", back_populates="user", foreign_keys="EventUser.user_id")
    notes_user = relationship("NoteUser", back_populates="user", foreign_keys="NoteUser.user_id")
    progress_days = relationship("ProgressDay", back_populates="user")


class RoleUser(Base):
    __tablename__ = "role_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    role = relationship("Role", back_populates="role_users")
    user = relationship("User", back_populates="role_users")


class UserDetail(Base):
    __tablename__ = "user_details"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    body_fat = Column(Float, nullable=True)  # % body fat
    occupation = Column(String(255), nullable=True)
    # Restrictions & preferences (comma-separated tags)
    allergies = Column(Text, nullable=True)
    intolerances = Column(Text, nullable=True)
    dislikes = Column(Text, nullable=True)
    injuries = Column(Text, nullable=True)
    equipment = Column(Text, nullable=True)
    food_preferences = Column(Text, nullable=True)
    country_code = Column(String(10), ForeignKey("countries.code"), nullable=True)
    gender_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    activity_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    status_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    objective_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    # Estado del ciclo de vida del cliente (independiente del estado CRM/status_id):
    # activo / pendiente / pausado / finalizado. Controla las pestañas de "Clientes".
    lifecycle_status = Column(String(20), nullable=False, default="activo", server_default="activo")
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    defecit = Column(Float, nullable=True)
    excedente = Column(Float, nullable=True)

    # ── Business / CRM fields ─────────────────────────────────────────────────
    plan_comprado = Column(String(255), nullable=True)
    precio = Column(Float, nullable=True)
    estado_pago = Column(String(50), nullable=True)          # pendiente / parcial / pagado
    importe_pagado = Column(Float, nullable=True)
    importe_pendiente = Column(Float, nullable=True)
    metodo_pago = Column(String(100), nullable=True)
    fecha_compra = Column(Date, nullable=True)
    fecha_limite_entrega = Column(Date, nullable=True)
    responsable_venta = Column(String(255), nullable=True)
    crm_origen = Column(String(255), nullable=True)
    whatsapp_link = Column(String(500), nullable=True)
    consentimiento_evolucion = Column(Boolean, nullable=True, default=False)
    fecha_renovacion = Column(Date, nullable=True)
    photo = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="detail", foreign_keys=[user_id])
    country = relationship("Country", foreign_keys=[country_code])
    gender = relationship("ParameterDetail", foreign_keys=[gender_id])
    activity = relationship("ParameterDetail", foreign_keys=[activity_id])
    status = relationship("ParameterDetail", foreign_keys=[status_id])
    objective = relationship("ParameterDetail", foreign_keys=[objective_id])

    # instructor relationship via user_parents (parent of this user)
    assigned_users = relationship(
        "UserDetail",
        secondary="user_parents",
        primaryjoin="UserDetail.id == foreign(UserParent.user_detail_id)",
        secondaryjoin="UserDetail.id == foreign(UserParent.parent_user_detail_id)",
        viewonly=True,
    )


class UserParent(Base):
    __tablename__ = "user_parents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    parent_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
