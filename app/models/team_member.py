from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False, unique=True)
    role_label = Column(String(100), nullable=True)
    hours_week = Column(Integer, nullable=True)
    salary_fijo = Column(Float, nullable=True)
    commission = Column(Float, nullable=True)
    variable_type = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=True, default='EUR')
    notes = Column(Text, nullable=True)
    permissions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_detail = relationship("UserDetail", foreign_keys=[user_detail_id])
