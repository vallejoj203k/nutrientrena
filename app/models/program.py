from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)          # recomposicion / perdida_grasa / ganancia_muscular / mantenimiento
    description = Column(Text, nullable=True)
    status = Column(String(20), default="activo")          # activo / archivado
    checkins_count = Column(Integer, default=0)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    coach = relationship("User", foreign_keys=[coach_id])
    phases = relationship("ProgramPhase", back_populates="program", order_by="ProgramPhase.order", cascade="all, delete-orphan")
    clients = relationship("ProgramClient", back_populates="program", cascade="all, delete-orphan")


class ProgramPhase(Base):
    __tablename__ = "program_phases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    weeks = Column(Integer, nullable=False, default=4)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    program = relationship("Program", back_populates="phases")


class ProgramClient(Base):
    __tablename__ = "program_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    program = relationship("Program", back_populates="clients")
    client = relationship("User", foreign_keys=[client_id])
