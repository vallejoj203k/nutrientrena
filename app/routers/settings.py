from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN
from app.core.responses import send_response
from app.models.app_setting import AppSetting

router = APIRouter(prefix="/settings", tags=["Settings"])


def _get_or_create(db: Session) -> AppSetting:
    s = db.query(AppSetting).filter(AppSetting.id == 1).first()
    if not s:
        s = AppSetting(id=1, currency="EUR", renewal_alert_days=30, timezone="Europe/Madrid")
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _out(s: AppSetting) -> dict:
    return {
        "business_name": s.business_name,
        "business_email": s.business_email,
        "business_phone": s.business_phone,
        "country": s.country,
        "currency": s.currency,
        "renewal_alert_days": s.renewal_alert_days,
        "timezone": s.timezone,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


class SettingsUpdate(BaseModel):
    business_name: Optional[str] = None
    business_email: Optional[str] = None
    business_phone: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    renewal_alert_days: Optional[int] = None
    timezone: Optional[str] = None


@router.get("")
def get_settings(
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN)),
):
    s = _get_or_create(db)
    return send_response(_out(s), "OK")


@router.put("")
def update_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN)),
):
    s = _get_or_create(db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return send_response(_out(s), "Ajustes guardados")
