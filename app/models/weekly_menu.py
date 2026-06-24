import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class WeeklyMenu(Base):
    __tablename__ = "weekly_menus"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_favorite = Column(Boolean, server_default="0", nullable=False)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    days = relationship("WeeklyMenuDay", order_by="WeeklyMenuDay.day_index", cascade="all, delete-orphan")


class WeeklyMenuDay(Base):
    __tablename__ = "weekly_menu_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(String(36), ForeignKey("weekly_menus.id", ondelete="CASCADE"), nullable=False)
    day_index = Column(Integer, nullable=False)  # 0=LUN … 6=DOM
    diet_id = Column(String(36), ForeignKey("diets.id", ondelete="SET NULL"), nullable=True)

    diet = relationship("Diet", foreign_keys=[diet_id])
