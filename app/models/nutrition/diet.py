from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Diet(Base):
    __tablename__ = "diets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    goal_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    calories = Column(Float, nullable=True)
    proteins = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    weeks = Column(Integer, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    state = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("User", back_populates="diets", foreign_keys=[client_id])
    instructor = relationship("User", foreign_keys=[instructor_id])
    category = relationship("ParameterDetail", foreign_keys=[category_id])
    goal = relationship("ParameterDetail", foreign_keys=[goal_id])
    details = relationship("DietDetail", back_populates="diet", cascade="all, delete-orphan")


class DietDetail(Base):
    __tablename__ = "diet_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diet_id = Column(Integer, ForeignKey("diets.id"), nullable=False)
    aliment_id = Column(Integer, ForeignKey("aliments.id"), nullable=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)
    meal_type_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    quantity = Column(Float, nullable=True)
    unit_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    diet = relationship("Diet", back_populates="details")
    aliment = relationship("Aliment", back_populates="diet_details")
    recipe = relationship("Recipe", back_populates="diet_details")
    meal_type = relationship("ParameterDetail", foreign_keys=[meal_type_id])
    unit = relationship("ParameterDetail", foreign_keys=[unit_id])
