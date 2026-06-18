from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.core.dependencies import (
    require_role_ids, verify_client_access, _get_coach_detail,
    SUPERADMIN, ADMIN, COACH,
)
from app.core.responses import send_response, send_error
from app.core.email import send_plan_email, _send, GMAIL_USER
from app.pdf.diet_pdf import generate_diet_pdf
from app.pdf.routine_pdf import generate_routine_pdf
from app.models.plan import PlanDelivery
from app.models.user import UserDetail, User
from app.models.parameter import ParameterDetail
from app.models.nutrition.diet import Diet, DietDetail, DietFood, DietFoodAliment
from app.models.routine import Routine, RoutineDay, RoutineDayDetail

router = APIRouter(prefix="/plans", tags=["Plans"])


def _get_state_id(db: Session, description: str) -> int | None:
    row = db.query(ParameterDetail).filter(
        ParameterDetail.description == description
    ).first()
    return row.id if row else None


def _build_diet_payload(diet_id: Optional[str], db: Session) -> dict | None:
    if not diet_id:
        return None
    diet = db.query(Diet).filter(Diet.id == diet_id).first()
    if not diet:
        return None
    detail = db.query(DietDetail).filter(DietDetail.diet_id == diet.id).first()
    foods  = db.query(DietFood).filter(DietFood.diet_id == diet.id).all()
    return {
        "title":    diet.title,
        "calories": diet.calories,
        "detail": {
            "proteins": detail.proteins if detail else None,
            "carbs":    detail.carbs    if detail else None,
            "fats":     detail.fats     if detail else None,
        } if detail else None,
        "foods": [
            {
                "name": f.name,
                "aliments": [
                    {
                        "name":     fa.aliment.name     if fa.aliment else "—",
                        "quantity": fa.quantity,
                        "calories": fa.aliment.calories if fa.aliment else None,
                    }
                    for fa in f.detail
                ],
            }
            for f in foods
        ],
    }


def _build_routine_payload(routine_id: Optional[int], db: Session) -> dict | None:
    if not routine_id:
        return None
    routine = db.query(Routine).filter(Routine.id == routine_id).first()
    if not routine:
        return None
    days = db.query(RoutineDay).filter(RoutineDay.routine_id == routine.id).all()

    def _all_details(day):
        details = list(day.details or [])
        for block in (day.blocks or []):
            details.extend(block.exercises or [])
        details.sort(key=lambda d: d.order_index or 0)
        return details

    return {
        "name":       routine.name,
        "days_count": routine.days,
        "days": [
            {
                "day_name":    d.day_name,
                "description": d.description,
                "exercises": [
                    {
                        "name":        det.training.name if det.training else "—",
                        "series":      det.series,
                        "repetitions": det.repetitions,
                        "break_time":  det.break_time,
                    }
                    for det in _all_details(d)
                ],
            }
            for d in days
        ],
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class PlanDeliverRequest(BaseModel):
    client_user_detail_id: str
    diet_id: Optional[str] = None
    routine_id: Optional[int] = None
    message: Optional[str] = None
    loom_link: Optional[str] = None
    send_email: bool = True


class PlanDeliveryOut(BaseModel):
    id: str
    client_user_detail_id: str
    coach_user_detail_id: Optional[str] = None
    diet_id: Optional[str] = None
    routine_id: Optional[int] = None
    diet_title: Optional[str] = None
    routine_name: Optional[str] = None
    message: Optional[str] = None
    loom_link: Optional[str] = None
    email_sent: bool
    delivered_at: datetime

    model_config = {"from_attributes": True}


# ── Deliver ───────────────────────────────────────────────────────────────────

@router.post("/deliver", summary="Entregar plan al cliente", description="Envía por email y registra la entrega de dieta y/o rutina al cliente.")
def deliver_plan(
    data: PlanDeliverRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    verify_client_access(data.client_user_detail_id, current_user, db)

    client_detail = db.query(UserDetail).filter(
        UserDetail.id == data.client_user_detail_id
    ).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    client_user = db.query(User).filter(User.id == client_detail.user_id).first()
    if not client_user:
        return send_error("Usuario del cliente no encontrado")

    diet_payload    = _build_diet_payload(data.diet_id, db)
    routine_payload = _build_routine_payload(data.routine_id, db)

    # ── Build PDF attachments ─────────────────────────────────────────────────
    attachments: list[tuple[bytes, str]] = []
    if data.diet_id:
        diet_obj = db.query(Diet).filter(Diet.id == data.diet_id).first()
        if diet_obj:
            try:
                attachments.append((generate_diet_pdf(diet_obj), "dieta.pdf"))
            except Exception as e:
                print(f"PDF diet error: {e}")
    if data.routine_id:
        routine_obj = db.query(Routine).filter(Routine.id == data.routine_id).first()
        if routine_obj:
            try:
                attachments.append((generate_routine_pdf(routine_obj), "rutina.pdf"))
            except Exception as e:
                print(f"PDF routine error: {e}")

    # ── Send email (optional) ─────────────────────────────────────────────────
    sent = False
    email_error = ""
    if data.send_email:
        sent, email_error = send_plan_email(
            to=client_user.email,
            client_name=client_detail.name,
            diet=diet_payload,
            routine=routine_payload,
            coach_message=data.message or "",
            loom_link=data.loom_link or "",
            attachments=attachments or None,
        )

    # ── Save delivery record ──────────────────────────────────────────────────
    coach_detail = _get_coach_detail(current_user.id, db)
    delivery = PlanDelivery(
        client_user_detail_id=data.client_user_detail_id,
        coach_user_detail_id=coach_detail.id if coach_detail else None,
        diet_id=data.diet_id,
        routine_id=data.routine_id,
        message=data.message,
        loom_link=data.loom_link,
        email_sent=sent,
        delivered_at=datetime.utcnow(),
    )
    db.add(delivery)

    # ── Update client state → "Plan entregado" ────────────────────────────────
    state_id = _get_state_id(db, "Plan entregado")
    if state_id:
        client_detail.status_id = state_id

    db.commit()
    db.refresh(delivery)

    return send_response(
        {
            "delivery": PlanDeliveryOut.model_validate(delivery).model_dump(),
            "email_sent": sent,
            "email_error": email_error,
            "client_email": client_user.email,
            "status_updated": state_id is not None,
        },
        "Plan entregado al cliente" if sent else "Plan registrado (email no enviado)",
    )


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history/{client_id}", summary="Historial de entregas", description="Retorna el historial de planes entregados a un cliente.")
def delivery_history(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    verify_client_access(client_id, current_user, db)

    deliveries = (
        db.query(PlanDelivery)
        .filter(PlanDelivery.client_user_detail_id == client_id)
        .order_by(PlanDelivery.delivered_at.desc())
        .all()
    )

    result = []
    for d in deliveries:
        item = PlanDeliveryOut.model_validate(d).model_dump()
        if d.diet_id:
            diet = db.query(Diet).filter(Diet.id == d.diet_id).first()
            item["diet_title"] = diet.title if diet else None
        if d.routine_id:
            routine = db.query(Routine).filter(Routine.id == d.routine_id).first()
            item["routine_name"] = routine.name if routine else None
        result.append(item)

    return send_response(result, "OK")


# ── Resend ────────────────────────────────────────────────────────────────────

@router.post("/resend/{delivery_id}", summary="Reenviar plan por email", description="Reenvía el email de una entrega de plan previamente registrada.")
def resend_delivery(
    delivery_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    delivery = db.query(PlanDelivery).filter(PlanDelivery.id == delivery_id).first()
    if not delivery:
        return send_error("Entrega no encontrada")

    verify_client_access(delivery.client_user_detail_id, current_user, db)

    client_detail = db.query(UserDetail).filter(
        UserDetail.id == delivery.client_user_detail_id
    ).first()
    client_user = db.query(User).filter(User.id == client_detail.user_id).first() if client_detail else None
    if not client_user:
        return send_error("Cliente no encontrado")

    diet_payload    = _build_diet_payload(delivery.diet_id, db)
    routine_payload = _build_routine_payload(delivery.routine_id, db)

    attachments: list[tuple[bytes, str]] = []
    if delivery.diet_id:
        diet_obj = db.query(Diet).filter(Diet.id == delivery.diet_id).first()
        if diet_obj:
            try:
                attachments.append((generate_diet_pdf(diet_obj), "dieta.pdf"))
            except Exception as e:
                print(f"PDF diet error: {e}")
    if delivery.routine_id:
        routine_obj = db.query(Routine).filter(Routine.id == delivery.routine_id).first()
        if routine_obj:
            try:
                attachments.append((generate_routine_pdf(routine_obj), "rutina.pdf"))
            except Exception as e:
                print(f"PDF routine error: {e}")

    sent, _ = send_plan_email(
        to=client_user.email,
        client_name=client_detail.name,
        diet=diet_payload,
        routine=routine_payload,
        coach_message=delivery.message or "",
        loom_link=delivery.loom_link or "",
        attachments=attachments or None,
    )

    return send_response(
        {"email_sent": sent},
        "Email reenviado correctamente" if sent else "No se pudo enviar el email",
    )


# ── Debug: test email ─────────────────────────────────────────────────────────

class TestEmailRequest(BaseModel):
    to: str

@router.post("/test-email", summary="Probar envío de email", description="Envía un email de prueba para verificar la configuración del proveedor de correo.")
def test_email(
    data: TestEmailRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    import os
    ok, err = _send(
        data.to,
        "Test de email — Nutrientrena",
        "<p>Este es un email de prueba enviado desde Nutrientrena.</p>",
    )
    return send_response(
        {
            "sent": ok,
            "error": err,
            "provider": "gmail" if GMAIL_USER else "resend",
            "resend_api_key_set": bool(os.environ.get("RESEND_API_KEY")),
            "gmail_user": GMAIL_USER or None,
            "mail_from": os.environ.get("MAIL_FROM", "onboarding@resend.dev"),
        },
        "OK" if ok else "Fallo al enviar",
    )
