from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=True)
    session_date = Column(Date, nullable=False)
    duration_min = Column(Integer, nullable=True)
    rpe = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    routine = relationship("Routine")
