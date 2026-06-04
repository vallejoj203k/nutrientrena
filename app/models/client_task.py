from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ClientTask(Base):
    __tablename__ = "client_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    task_type = Column(String(20), nullable=False)   # rutina/cardio/descanso/nutricion/checkin/foto/mensaje/video/sesion
    title = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    done = Column(Boolean, default=False)
    week_date = Column(Date, nullable=False)          # Monday of the target week
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
