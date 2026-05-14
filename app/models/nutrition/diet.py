import uuid
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Diet(Base):
    __tablename__ = "diets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    calories = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    type_id = Column(Integer, ForeignKey("type_foods.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    type = relationship("TypeFood", foreign_keys=[type_id])
    user = relationship("User", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_user_id])
    detail = relationship("DietDetail", back_populates="diet", uselist=False,
                          cascade="all, delete-orphan")
    foods = relationship("DietFood", back_populates="diet", cascade="all, delete-orphan",
                         order_by="DietFood.id")


class DietDetail(Base):
    __tablename__ = "diet_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diet_id = Column(String(36), ForeignKey("diets.id"), nullable=False)
    gender_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    body_fat = Column(Float, nullable=True)
    level_activity_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    objective_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    proteins = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    deficit = Column(Float, nullable=True)
    surplus = Column(Float, nullable=True)

    diet = relationship("Diet", back_populates="detail")
    gender = relationship("ParameterDetail", foreign_keys=[gender_id])
    level_activity = relationship("ParameterDetail", foreign_keys=[level_activity_id])
    objective = relationship("ParameterDetail", foreign_keys=[objective_id])


class DietFood(Base):
    __tablename__ = "diet_foods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diet_id = Column(String(36), ForeignKey("diets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    diet = relationship("Diet", back_populates="foods")
    detail = relationship("DietFoodAliment", back_populates="diet_food",
                          cascade="all, delete-orphan", order_by="DietFoodAliment.order")


class DietFoodAliment(Base):
    __tablename__ = "diet_food_aliments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diet_id = Column(String(36), ForeignKey("diets.id"), nullable=False)
    diet_food_id = Column(Integer, ForeignKey("diet_foods.id"), nullable=False)
    aliment_id = Column(String(36), ForeignKey("aliments.id"), nullable=False)
    quantity = Column(Float, nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    diet_food = relationship("DietFood", back_populates="detail")
    aliment = relationship("Aliment", back_populates="diet_food_aliments")
