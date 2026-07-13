from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Document(Base):
    """Un PDF (u otro archivo) subido por el coach a su librería de Documentos.

    category agrupa los documentos en la Librería › Documentos:
    "contratos" / "guias" / "plantillas".
    client_user_detail_id queda disponible para asignar/compartir con un
    cliente concreto en el futuro (hoy siempre null = librería del coach).
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=True)
    name = Column(String(255), nullable=False)
    category = Column(String(30), nullable=False, default="guias")
    file_url = Column(String(500), nullable=False)
    file_key = Column(String(500), nullable=True)
    size_kb = Column(Float, nullable=True)
    content_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    coach = relationship("User", foreign_keys=[coach_id])
