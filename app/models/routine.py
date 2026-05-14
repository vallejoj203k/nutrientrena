from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Routine(Base):
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    weeks = Column(Integer, nullable=True)
    state = Column(Integer, default=1)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("User", back_populates="routines", foreign_keys=[client_id])
    instructor = relationship("User", foreign_keys=[instructor_id])
    days = relationship("RoutineDay", back_populates="routine", cascade="all, delete-orphan")


class RoutineDay(Base):
    __tablename__ = "routine_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=False)
    name = Column(String(255), nullable=True)
    day_number = Column(Integer, nullable=True)
    rest = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    routine = relationship("Routine", back_populates="days")
    details = relationship("RoutineDayDetail", back_populates="routine_day", cascade="all, delete-orphan")


class RoutineDayDetail(Base):
    __tablename__ = "routine_day_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    routine_day_id = Column(Integer, ForeignKey("routine_days.id"), nullable=False)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    sets = Column(Integer, nullable=True)
    reps = Column(String(50), nullable=True)
    weight = Column(Float, nullable=True)
    rest_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    routine_day = relationship("RoutineDay", back_populates="details")
    training = relationship("Training", back_populates="routine_day_details")
