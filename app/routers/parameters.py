from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.parameter import Parameter, ParameterDetail

router_params = APIRouter(prefix="/parameters", tags=["Parameters"])
router_details = APIRouter(prefix="/parameters-detail", tags=["Parameters"])


@router_params.get("/search")
def search_parameters(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Parameter)
    if search:
        q = q.filter(Parameter.description.ilike(f"%{search}%"))
    items = q.all()
    return [{"id": p.id, "description": p.description} for p in items]


@router_details.get("/search")
def search_details(
    parameter_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(ParameterDetail)
    if parameter_id:
        q = q.filter(ParameterDetail.parameter_id == parameter_id)
    if search:
        q = q.filter(ParameterDetail.description.ilike(f"%{search}%"))
    items = q.all()
    return [
        {
            "id": d.id,
            "parameter_id": d.parameter_id,
            "description": d.description,
            "value_1": d.value_1,
            "value_1_description": d.value_1_description,
        }
        for d in items
    ]
