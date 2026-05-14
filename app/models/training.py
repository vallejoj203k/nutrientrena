from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"), nullable=True)
    image = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    state = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    muscle_group = relationship("MuscleGroup", back_populates="trainings")
    routine_day_details = relationship("RoutineDayDetail", back_populates="training")


class TrainingClient(Base):
    __tablename__ = "training_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    training = relationship("Training")
    user = relationship("User")
