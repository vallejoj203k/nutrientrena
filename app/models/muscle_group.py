from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class MuscleGroup(Base):
    __tablename__ = "muscle_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    image = Column(String(500), nullable=True)
    state = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    trainings = relationship("Training", back_populates="muscle_group")


class MuscleGroupClient(Base):
    __tablename__ = "muscle_group_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    muscle_group = relationship("MuscleGroup")
    user = relationship("User")
