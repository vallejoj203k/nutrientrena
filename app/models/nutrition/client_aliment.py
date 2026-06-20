import uuid
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Text
from datetime import datetime
from app.database import Base


class ClientAliment(Base):
    __tablename__ = "client_aliments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_food_id = Column(Integer, ForeignKey("group_foods.id"), nullable=True)
    brand = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=True)
    proteins = Column(Float, nullable=True)
    carbohydrates = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    calories = Column(Float, nullable=True)
    comments = Column(Text, nullable=True)
    created_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
