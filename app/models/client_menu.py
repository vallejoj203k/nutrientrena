from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ClientMenu(Base):
    """Menú semanal asignado a un cliente por su coach.

    Un cliente puede tener asignaciones históricas; la vigente es la más
    reciente por assigned_at.
    """
    __tablename__ = "client_menus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    menu_id = Column(String(36), ForeignKey("weekly_menus.id", ondelete="CASCADE"), nullable=False)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    menu = relationship("WeeklyMenu")
