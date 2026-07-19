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
    secondary_muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"), nullable=True)  # first of the set (back-compat)
    secondary_muscle_group_ids = Column(Text, nullable=True)  # comma-separated muscle group ids
    image = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    exercise_type = Column(String(20), nullable=True)  # compound/isolation/cardio/mobility
    location = Column(String(20), nullable=True)  # gym/home/outdoor/both
    material = Column(String(120), nullable=True)  # Barra, Mancuernas, Sin equipo…
    difficulty = Column(Integer, nullable=True)  # 1 Principiante / 2 Intermedio / 3 Avanzado
    movement_pattern = Column(String(255), nullable=True)  # Empuje horizontal, Bisagra de cadera…
    rec_series = Column(String(40), nullable=True)  # series recomendadas, ej. "3-4"
    rec_reps = Column(String(40), nullable=True)    # reps recomendadas, ej. "8-12"
    rec_rest = Column(String(40), nullable=True)    # descanso recomendado, ej. "60-90s"
    state = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    muscle_group = relationship("MuscleGroup", foreign_keys=[muscle_group_id], back_populates="trainings")
    secondary_muscle_group = relationship("MuscleGroup", foreign_keys=[secondary_muscle_group_id])
    routine_day_details = relationship("RoutineDayDetail", back_populates="training")


class TrainingClient(Base):
    __tablename__ = "training_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    training = relationship("Training")
    user = relationship("User")
