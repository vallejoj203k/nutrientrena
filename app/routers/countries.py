from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.country import Country

router = APIRouter(prefix="/countries", tags=["Countries"])


@router.get("/search")
def search(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Country)
    if search:
        q = q.filter(Country.country.ilike(f"%{search}%"))
    items = q.limit(50).all()
    return [{"id": c.id, "code": c.code, "country": c.country} for c in items]
