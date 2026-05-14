from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Aliment(Base):
    __tablename__ = "aliments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type_food_id = Column(Integer, ForeignKey("type_foods.id"), nullable=True)
    group_food_id = Column(Integer, ForeignKey("group_foods.id"), nullable=True)
    unit_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    calories = Column(Float, nullable=True)
    proteins = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    fiber = Column(Float, nullable=True)
    sugar = Column(Float, nullable=True)
    sodium = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    state = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    type_food = relationship("TypeFood", back_populates="aliments")
    group_food = relationship("GroupFood", back_populates="aliments")
    unit = relationship("ParameterDetail", foreign_keys=[unit_id])
    diet_details = relationship("DietDetail", back_populates="aliment")
    recipe_details = relationship("RecipeDetail", back_populates="aliment")
