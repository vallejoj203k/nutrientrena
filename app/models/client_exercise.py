from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ClientExercise(Base):
    __tablename__ = "client_exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"), nullable=True)
    secondary_muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"), nullable=True)
    image = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    exercise_type = Column(String(20), nullable=True)  # compound/isolation/cardio/mobility
    location = Column(String(20), nullable=True)  # gym/home/outdoor/both
    created_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    muscle_group = relationship("MuscleGroup", foreign_keys=[muscle_group_id])
    secondary_muscle_group = relationship("MuscleGroup", foreign_keys=[secondary_muscle_group_id])
