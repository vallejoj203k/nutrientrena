from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ContractTemplate(Base):
    __tablename__ = "contract_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, default="servicio")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    coach = relationship("User", foreign_keys=[coach_id])
    contracts = relationship("Contract", back_populates="template")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("user_details.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("contract_templates.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, default="servicio")
    content = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="borrador")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    coach = relationship("User", foreign_keys=[coach_id])
    client = relationship("UserDetail", foreign_keys=[client_id])
    template = relationship("ContractTemplate", back_populates="contracts", foreign_keys=[template_id])
