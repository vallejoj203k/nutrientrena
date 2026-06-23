from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.core.responses import send_response, send_error
from app.models.form import FormAssignment, FormResponse, PROFILE_FIELD_MAP
from app.models.user import UserDetail, UserParent, User
from app.models.parameter import Parameter, ParameterDetail
from app.schemas.form import FormAssignmentOut, FormSubmitRequest

router = APIRouter(prefix="/public", tags=["Public"])

_CLIENT_STATE_CACHE: dict = {}

# Parameter names that map to form field keys (no auth needed for these)
_FORM_PARAM_NAMES = {
    "gender_id":    "Genero",
    "activity_id":  "Nivel de actividad",
    "objective_id": "Objetivo Usuario",
}


@router.get("/form-options", summary="Opciones de formulario público")
def get_form_options(db: Session = Depends(get_db)):
    result = {}
    for field_key, param_name in _FORM_PARAM_NAMES.items():
        param = db.query(Parameter).filter(Parameter.description == param_name).first()
        if param:
            result[field_key] = [
                {"id": d.id, "label": d.description}
                for d in db.query(ParameterDetail)
                    .filter(ParameterDetail.parameter_id == param.id)
                    .order_by(ParameterDetail.id)
                    .all()
            ]
        else:
            result[field_key] = []
    return send_response(result, "OK")


def _get_client_state_id(db: Session, description: str) -> int | None:
    if description not in _CLIENT_STATE_CACHE:
        row = db.query(ParameterDetail).filter(
            ParameterDetail.description == description
        ).first()
        if row:
            _CLIENT_STATE_CACHE[description] = row.id
    return _CLIENT_STATE_CACHE.get(description)


def _get_coach_for_client(client_detail_id: str, db: Session):
    parent = db.query(UserParent).filter(
        UserParent.user_detail_id == client_detail_id
    ).first()
    if not parent:
        return None, None
    coach_detail = db.query(UserDetail).filter(
        UserDetail.id == parent.parent_user_detail_id
    ).first()
    if not coach_detail:
        return None, None
    coach_user = db.query(User).filter(User.id == coach_detail.user_id).first()
    return coach_detail, coach_user


@router.get("/form/{assignment_id}", summary="Ver formulario público", description="Retorna el formulario asignado sin autenticación (para que el cliente lo complete).")
def get_public_form(assignment_id: str, db: Session = Depends(get_db)):
    assignment = db.query(FormAssignment).filter(FormAssignment.id == assignment_id).first()
    if not assignment:
        return send_error("Formulario no encontrado", code=404)
    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "OK")


@router.post("/form/{assignment_id}/submit", summary="Enviar formulario público", description="El cliente envía sus respuestas sin necesitar autenticación. Actualiza su perfil automáticamente.")
def submit_public_form(
    assignment_id: str,
    data: FormSubmitRequest,
    db: Session = Depends(get_db),
):
    assignment = db.query(FormAssignment).filter(FormAssignment.id == assignment_id).first()
    if not assignment:
        return send_error("Formulario no encontrado", code=404)
    if assignment.status == "submitted":
        return send_error("Este formulario ya fue enviado", code=400)

    db.query(FormResponse).filter(FormResponse.form_assignment_id == assignment_id).delete()

    for item in data.responses:
        db.add(FormResponse(
            form_assignment_id=assignment_id,
            field_key=item.field_key,
            value=item.value,
        ))

    client = db.query(UserDetail).filter(
        UserDetail.id == assignment.client_user_detail_id
    ).first()

    if client:
        for item in data.responses:
            profile_field = PROFILE_FIELD_MAP.get(item.field_key)
            if profile_field and item.value is not None:
                try:
                    current_val = getattr(client, profile_field)
                    if isinstance(current_val, float) or profile_field in ("weight", "height"):
                        setattr(client, profile_field, float(item.value))
                    elif profile_field.endswith("_id"):
                        setattr(client, profile_field, int(item.value))
                    else:
                        setattr(client, profile_field, item.value)
                except (ValueError, TypeError):
                    pass

        client.status_id = _get_client_state_id(db, "Formulario recibido")

    assignment.status = "submitted"
    assignment.submitted_at = datetime.utcnow()
    db.commit()

    # Notify coach
    if client:
        coach_detail, coach_user = _get_coach_for_client(client.id, db)
        if coach_user and coach_user.email:
            from app.core.email import notify_coach_form_submitted
            client_name = f"{client.name or ''} {client.last_name or ''}".strip() or "Cliente"
            coach_name  = f"{coach_detail.name or ''} {coach_detail.last_name or ''}".strip() or "Coach"
            client_user = db.query(User).filter(User.id == client.user_id).first()
            notify_coach_form_submitted(
                coach_email=coach_user.email,
                coach_name=coach_name,
                client_name=client_name,
                client_email=client_user.email if client_user else "",
            )

    db.refresh(assignment)
    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "Formulario enviado correctamente")
