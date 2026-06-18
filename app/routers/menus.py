from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import require_roles
from app.core.responses import send_response
from app.models.menu import Menu
from app.schemas.auth import MenuOut

router = APIRouter(prefix="/menus", tags=["Menus"])


@router.get("/findAll", summary="Listar menús", description="Retorna todos los menús del sistema (solo admin).")
def find_all(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    menus = db.query(Menu).all()
    return send_response([MenuOut.model_validate(m).model_dump() for m in menus], "OK")
