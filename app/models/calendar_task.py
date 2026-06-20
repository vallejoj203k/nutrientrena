import calendar as _cal
from sqlalchemy import Column, Integer, String, Boolean, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


VALID_TASK_TYPES = {
    "rutina", "cardio", "descanso", "nutricion", "checkin",
    "foto", "mensaje", "video", "sesion", "otro",
}

COLOR_MAP = {
    "rutina":    "#4F46E5",
    "cardio":    "#EF4444",
    "descanso":  "#6B7280",
    "nutricion": "#10B981",
    "checkin":   "#F59E0B",
    "foto":      "#8B5CF6",
    "mensaje":   "#3B82F6",
    "video":     "#EC4899",
    "sesion":    "#0EA5E9",
    "otro":      "#9CA3AF",
}


class CalendarTask(Base):
    __tablename__ = "calendar_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    coach_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    task_date = Column(Date, nullable=False)
    task_type = Column(String(30), nullable=False)
    title = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    color = Column(String(20), nullable=True)

    done = Column(Boolean, default=False)
    done_at = Column(DateTime, nullable=True)

    # Recurrence
    recurrence = Column(String(20), default="none")       # none / daily / weekly / monthly
    recurrence_end_date = Column(Date, nullable=True)
    recurrence_group_id = Column(Integer, nullable=True)

    # Link to actual check-in when task_type = 'checkin'
    checkin_id = Column(String(36), ForeignKey("weekly_checkins.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("UserDetail", foreign_keys=[client_user_detail_id])
    coach = relationship("User", foreign_keys=[coach_user_id])
    checkin = relationship("WeeklyCheckin", foreign_keys=[checkin_id])
