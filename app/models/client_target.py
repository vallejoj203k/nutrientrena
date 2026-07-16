from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ClientTarget(Base):
    __tablename__ = "client_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    target_weight = Column(Float, nullable=True)
    target_body_fat = Column(Float, nullable=True)
    target_muscle_mass = Column(Float, nullable=True)
    calories = Column(Float, nullable=True)
    proteins = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    deficit = Column(Float, nullable=True)   # % below TDEE
    surplus = Column(Float, nullable=True)   # % above TDEE
    # Ajustes del planificador de macros (g por kg de masa corporal magra)
    protein_ratio = Column(Float, nullable=True)  # default 2.0 g/kg MCM
    fat_ratio = Column(Float, nullable=True)      # default 0.9 g/kg MCM
    meal_count = Column(Integer, nullable=True)   # nº de comidas/día (3-6)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="client_target")
