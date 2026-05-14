from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.menu import Menu
from app.schemas.auth import MenuOut
from app.models.role import SUPERADMIN

router = APIRouter(prefix="/menus", tags=["Menus"])


@router.get("/findAll")
def find_all(
    db: Session = Depends(get_db),
    _=Depends(require_roles(SUPERADMIN)),
):
    menus = db.query(Menu).all()
    return [MenuOut.model_validate(m) for m in menus]
