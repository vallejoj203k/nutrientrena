from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH
from app.core.responses import send_response
from app.models.nutrition.diet import Pathology

router = APIRouter(prefix="/pathologies", tags=["Nutrition - Pathologies"])


@router.get("/findAll", summary="Listar patologías")
def find_all(db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    items = db.query(Pathology).filter(Pathology.state == 1).order_by(Pathology.id).all()
    return send_response([{"id": p.id, "name": p.name} for p in items], "OK")
