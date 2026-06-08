from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response
from app.models.country import Country

router = APIRouter(prefix="/countries", tags=["Countries"])


@router.get("/search", summary="Buscar países", description="Busca países por nombre, retorna máximo 50 resultados.")
def search(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(Country)
    if search:
        q = q.filter(Country.country.ilike(f"%{search}%"))
    items = q.limit(50).all()
    return send_response(
        [{"id": c.id, "code": c.code, "country": c.country} for c in items],
        "OK",
    )
