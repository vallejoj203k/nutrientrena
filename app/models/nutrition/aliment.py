import uuid
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class AlimentDescription(Base):
    __tablename__ = "aliment_descriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aliment_id = Column(String(36), ForeignKey("aliments.id"), nullable=False)
    vita = Column(Float, nullable=True)
    vitb1 = Column(Float, nullable=True)
    vitb2 = Column(Float, nullable=True)
    vitb3 = Column(Float, nullable=True)
    vitb5 = Column(Float, nullable=True)
    vitb6 = Column(Float, nullable=True)
    vitb9 = Column(Float, nullable=True)
    vitb12 = Column(Float, nullable=True)
    vitc = Column(Float, nullable=True)
    vitd = Column(Float, nullable=True)
    vite = Column(Float, nullable=True)
    vitk = Column(Float, nullable=True)
    calina = Column(Float, nullable=True)
    calcium = Column(Float, nullable=True)
    copper = Column(Float, nullable=True)
    iron = Column(Float, nullable=True)
    magnesium = Column(Float, nullable=True)
    manganese = Column(Float, nullable=True)
    phosphorus = Column(Float, nullable=True)
    potassium = Column(Float, nullable=True)
    selenium = Column(Float, nullable=True)
    sodium = Column(Float, nullable=True)
    zinc = Column(Float, nullable=True)
    water = Column(Float, nullable=True)
    fiber = Column(Float, nullable=True)
    cholesterol = Column(Float, nullable=True)
    saturated_fats = Column(Float, nullable=True)
    mono_saturated_fats = Column(Float, nullable=True)
    poli_saturated_fats = Column(Float, nullable=True)
    glycemic_index = Column(Float, nullable=True)

    aliment = relationship("Aliment", back_populates="description")


class Aliment(Base):
    __tablename__ = "aliments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_food_id = Column(Integer, ForeignKey("group_foods.id"), nullable=True)
    brand = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=True)
    quantity_unit = Column(String(20), nullable=True, default='g')
    quantity_type_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    proteins = Column(Float, nullable=True)
    carbohydrates = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    calories = Column(Float, nullable=True)
    comments = Column(Text, nullable=True)
    parent_id = Column(String(36), ForeignKey("aliments.id"), nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    created_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group_food = relationship("GroupFood", back_populates="aliments")
    quantity_type = relationship("ParameterDetail", foreign_keys=[quantity_type_id])
    description = relationship("AlimentDescription", back_populates="aliment", uselist=False, cascade="all, delete-orphan")
    parent = relationship("Aliment", remote_side=[id], foreign_keys=[parent_id])
    diet_food_aliments = relationship("DietFoodAliment", back_populates="aliment")
    recipe_details = relationship("RecipeDetail", back_populates="aliment")
