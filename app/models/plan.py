import uuid
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class PlanDelivery(Base):
    __tablename__ = "plan_deliveries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    coach_user_detail_id  = Column(String(36), ForeignKey("user_details.id"), nullable=True)
    diet_id    = Column(String(36), ForeignKey("diets.id"), nullable=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=True)
    message    = Column(Text, nullable=True)
    loom_link  = Column(String(500), nullable=True)
    email_sent = Column(Boolean, default=False, nullable=False)
    delivered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    client  = relationship("UserDetail", foreign_keys=[client_user_detail_id])
    coach   = relationship("UserDetail", foreign_keys=[coach_user_detail_id])
    diet    = relationship("Diet",    foreign_keys=[diet_id])
    routine = relationship("Routine", foreign_keys=[routine_id])
