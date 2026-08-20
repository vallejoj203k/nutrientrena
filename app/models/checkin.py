import uuid
from sqlalchemy import Column, String, Float, Integer, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class WeeklyCheckin(Base):
    __tablename__ = "weekly_checkins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    coach_user_detail_id  = Column(String(36), ForeignKey("user_details.id"), nullable=True)
    checkin_date = Column(Date, nullable=False)
    weight       = Column(Float, nullable=True)
    notes        = Column(Text, nullable=True)
    coach_notes  = Column(Text, nullable=True)
    photo_url    = Column(String(500), nullable=True)
    photo2       = Column(String(500), nullable=True)
    photo3       = Column(String(500), nullable=True)
    # ── Cómo se ha sentido la semana, de 0 a 10 ────────────────────────────
    # Las rellena el CLIENTE al enviar su check-in. La ficha del cliente ya
    # intentaba pintarlas desde hace tiempo —y siempre salía "—"— porque el
    # campo no existía: estaban pensadas y sin implementar.
    energy       = Column(Integer, nullable=True)   # energía
    effort       = Column(Integer, nullable=True)   # esfuerzo en los entrenos
    hunger       = Column(Integer, nullable=True)   # hambre / adherencia a la dieta
    sleep        = Column(Integer, nullable=True)   # descanso
    # Cuándo lo revisó el coach. Antes solo se sabía si había escrito notas, y
    # "lo he leído y está todo bien" no deja notas: la bandeja no podía
    # distinguir lo pendiente de lo atendido.
    reviewed_at  = Column(DateTime, nullable=True)
    reviewed_by_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=True)
    body_fat     = Column(Float, nullable=True)
    muscle_mass  = Column(Float, nullable=True)
    waist        = Column(Float, nullable=True)
    chest        = Column(Float, nullable=True)
    hips         = Column(Float, nullable=True)
    arms         = Column(Float, nullable=True)
    legs         = Column(Float, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("UserDetail", foreign_keys=[client_user_detail_id])
    coach  = relationship("UserDetail", foreign_keys=[coach_user_detail_id])
