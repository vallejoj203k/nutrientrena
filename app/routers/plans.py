from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.core.email import send_plan_email
from app.models.user import UserDetail, User
from app.models.parameter import ParameterDetail
from app.models.nutrition.diet import Diet, DietDetail, DietFood
from app.models.routine import Routine, RoutineDay

router = APIRouter(prefix="/plans", tags=["Plans"])


def _get_state_id(db: Session, description: str) -> int | None:
    row = db.query(ParameterDetail).filter(
        ParameterDetail.description == description
    ).first()
    return row.id if row else None


class PlanDeliverRequest(BaseModel):
    client_user_detail_id: str
    diet_id: Optional[str] = None
    routine_id: Optional[int] = None
    message: Optional[str] = None


@router.post("/deliver")
def deliver_plan(
    data: PlanDeliverRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    client_detail = db.query(UserDetail).filter(
        UserDetail.id == data.client_user_detail_id
    ).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    client_user = db.query(User).filter(User.id == client_detail.user_id).first()
    if not client_user:
        return send_error("Usuario del cliente no encontrado")

    # Construir payload de dieta
    diet_payload = None
    if data.diet_id:
        diet = db.query(Diet).filter(Diet.id == data.diet_id).first()
        if diet:
            detail = db.query(DietDetail).filter(DietDetail.diet_id == diet.id).first()
            foods  = db.query(DietFood).filter(DietFood.diet_id == diet.id).all()
            diet_payload = {
                "title":    diet.title,
                "calories": diet.calories,
                "detail":   {
                    "proteins": detail.proteins if detail else None,
                    "carbs":    detail.carbs    if detail else None,
                    "fats":     detail.fats     if detail else None,
                } if detail else None,
                "foods": [{"name": f.name} for f in foods],
            }

    # Construir payload de rutina
    routine_payload = None
    if data.routine_id:
        routine = db.query(Routine).filter(Routine.id == data.routine_id).first()
        if routine:
            days = db.query(RoutineDay).filter(
                RoutineDay.routine_id == routine.id
            ).all()
            routine_payload = {
                "name":       routine.name,
                "days_count": routine.days,
                "days": [{"day_name": d.day_name, "description": d.description} for d in days],
            }

    # Enviar email
    sent = send_plan_email(
        to=client_user.email,
        client_name=client_detail.name,
        diet=diet_payload,
        routine=routine_payload,
        coach_message=data.message or "",
    )

    # Actualizar estado del cliente → "Plan entregado"
    state_id = _get_state_id(db, "Plan entregado")
    if state_id:
        client_detail.status_id = state_id
        db.commit()

    return send_response(
        {
            "email_sent": sent,
            "client_email": client_user.email,
            "status_updated": state_id is not None,
        },
        "Plan entregado al cliente" if sent else "Estado actualizado (email no configurado)",
    )
