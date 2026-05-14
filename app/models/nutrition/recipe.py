from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    calories = Column(Float, nullable=True)
    proteins = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    servings = Column(Integer, nullable=True)
    prep_time = Column(Integer, nullable=True)
    image = Column(String(500), nullable=True)
    state = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    instructor = relationship("User")
    category = relationship("ParameterDetail", foreign_keys=[category_id])
    details = relationship("RecipeDetail", back_populates="recipe", cascade="all, delete-orphan")
    diet_details = relationship("DietDetail", back_populates="recipe")


class RecipeDetail(Base):
    __tablename__ = "recipe_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    aliment_id = Column(Integer, ForeignKey("aliments.id"), nullable=False)
    quantity = Column(Float, nullable=True)
    unit_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)

    recipe = relationship("Recipe", back_populates="details")
    aliment = relationship("Aliment", back_populates="recipe_details")
    unit = relationship("ParameterDetail", foreign_keys=[unit_id])
