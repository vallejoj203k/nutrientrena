from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean
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

    slug = Column(String(255), nullable=True, unique=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    document = Column(String(50), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    gender_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    state = Column(Integer, default=1)
    photo = Column(String(500), nullable=True)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    activity_level_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    training_level_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    goal_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role = relationship("Role", back_populates="users")
    country = relationship("Country", foreign_keys=[country_id])
    clients = relationship("User", foreign_keys=[instructor_id], backref="instructor")
    routines = relationship("Routine", back_populates="client", foreign_keys="Routine.client_id")
    diets = relationship("Diet", back_populates="client", foreign_keys="Diet.client_id")
    events = relationship("EventUser", back_populates="user")
    notes_user = relationship("NoteUser", back_populates="user")
    progress_days = relationship("ProgressDay", back_populates="user")
    client_target = relationship("ClientTarget", back_populates="user", uselist=False)
