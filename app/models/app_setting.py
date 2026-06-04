from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    business_name = Column(String(255), nullable=True)
    business_email = Column(String(255), nullable=True)
    business_phone = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=True, default="EUR")
    renewal_alert_days = Column(Integer, nullable=True, default=30)
    timezone = Column(String(50), nullable=True, default="Europe/Madrid")
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
