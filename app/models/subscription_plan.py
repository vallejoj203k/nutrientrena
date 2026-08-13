"""Los planes que Alzum le vende a un coach.

Ojo con el nombre: ya existe `PlanDelivery`, que es OTRA cosa —el envío de un
plan de dieta y rutina a un cliente—. Aquí se habla de la tarifa: lo que un
coach paga a Alzum. La pantalla lo dice en su subtítulo justamente porque las
dos cosas se llaman igual en castellano y se confunden solas.

Esto es el CATÁLOGO, no la facturación. Definir cuánto cuesta el plan Pro no
necesita pasarela de pago; cobrarlo sí, y eso sigue fuera de alcance.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.database import Base

CICLOS = ("mensual", "anual")


class SubscriptionPlan(Base):
    __tablename__ = "platform_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), nullable=False)
    price_month = Column(Float, nullable=False, default=0, server_default="0")
    # Precio POR MES pagando al año, no el total anual: es como lo enseña la
    # web de precios ("15 €/mes pagando anual") y como lo pide el formulario.
    price_year_month = Column(Float, nullable=True)
    default_cycle = Column(String(10), nullable=False, default="mensual", server_default="mensual")
    # 0 = sin límite. Se usa el cero y no NULL para que "ilimitado" sea una
    # decisión escrita y no un campo que alguien se dejó vacío.
    max_clients = Column(Integer, nullable=False, default=0, server_default="0")
    coaches_included = Column(Integer, nullable=False, default=1, server_default="1")
    extra_coach_price = Column(Float, nullable=True)
    storage = Column(String(60), nullable=True)
    support = Column(String(120), nullable=True)
    # Una funcionalidad por línea, tal como se escriben en el formulario.
    features = Column(Text, nullable=True)
    visible = Column(Boolean, nullable=False, default=True, server_default="1")
    highlighted = Column(Boolean, nullable=False, default=False, server_default="0")
    order_index = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
