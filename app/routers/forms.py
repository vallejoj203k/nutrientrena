from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.models.form import FormTemplate, FormTemplateField, FormAssignment, FormResponse, PROFILE_FIELD_MAP
from app.models.user import UserDetail
from app.models.parameter import ParameterDetail
from app.schemas.form import (
    FormTemplateCreate, FormTemplateUpdate, FormTemplateOut,
    FormAssignRequest, FormSubmitRequest, FormAssignmentOut,
)

router_templates = APIRouter(prefix="/form-templates", tags=["Forms - Templates"])
router_assignments = APIRouter(prefix="/form-assignments", tags=["Forms - Assignments"])

_CLIENT_STATE_CACHE: dict = {}


def _get_client_state_id(db: Session, description: str) -> int | None:
    if description not in _CLIENT_STATE_CACHE:
        row = db.query(ParameterDetail).filter(
            ParameterDetail.description == description
        ).first()
        if row:
            _CLIENT_STATE_CACHE[description] = row.id
    return _CLIENT_STATE_CACHE.get(description)


# ── Templates ─────────────────────────────────────────────────────────────────

@router_templates.post("")
def create_template(data: FormTemplateCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if data.is_default:
        db.query(FormTemplate).filter(
            FormTemplate.created_by == current_user.id,
            FormTemplate.is_default.is_(True),
        ).update({"is_default": False})

    template = FormTemplate(
        title=data.title,
        description=data.description,
        is_default=data.is_default,
        created_by=current_user.id,
    )
    db.add(template)
    db.flush()

    for i, field in enumerate(data.fields):
        db.add(FormTemplateField(
            form_template_id=template.id,
            label=field.label,
            field_type=field.field_type,
            field_key=field.field_key,
            placeholder=field.placeholder,
            options=field.options,
            order=field.order or i,
            required=field.required,
        ))

    db.commit()
    db.refresh(template)
    return send_response(FormTemplateOut.model_validate(template).model_dump(), "Plantilla creada")


@router_templates.get("/default")
def get_default(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    template = db.query(FormTemplate).filter(
        FormTemplate.is_default.is_(True),
    ).first()
    if not template:
        return send_error("No hay plantilla por defecto")
    return send_response(FormTemplateOut.model_validate(template).model_dump(), "OK")


@router_templates.get("")
def list_templates(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    templates = db.query(FormTemplate).filter(FormTemplate.created_by == current_user.id).all()
    return send_response([FormTemplateOut.model_validate(t).model_dump() for t in templates], "OK")


@router_templates.get("/{id}")
def get_template(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    template = db.query(FormTemplate).filter(FormTemplate.id == id).first()
    if not template:
        return send_error("Plantilla no encontrada")
    return send_response(FormTemplateOut.model_validate(template).model_dump(), "OK")


@router_templates.put("/{id}")
def update_template(id: int, data: FormTemplateUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    template = db.query(FormTemplate).filter(FormTemplate.id == id).first()
    if not template:
        return send_error("Plantilla no encontrada")

    if data.title is not None:
        template.title = data.title
    if data.description is not None:
        template.description = data.description
    if data.is_default is not None:
        if data.is_default:
            db.query(FormTemplate).filter(
                FormTemplate.created_by == current_user.id,
                FormTemplate.is_default.is_(True),
                FormTemplate.id != id,
            ).update({"is_default": False})
        template.is_default = data.is_default

    if data.fields is not None:
        db.query(FormTemplateField).filter(FormTemplateField.form_template_id == id).delete()
        for i, field in enumerate(data.fields):
            db.add(FormTemplateField(
                form_template_id=id,
                label=field.label,
                field_type=field.field_type,
                field_key=field.field_key,
                placeholder=field.placeholder,
                options=field.options,
                order=field.order or i,
                required=field.required,
            ))

    db.commit()
    db.refresh(template)
    return send_response(FormTemplateOut.model_validate(template).model_dump(), "Plantilla actualizada")


@router_templates.delete("/{id}")
def delete_template(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    template = db.query(FormTemplate).filter(FormTemplate.id == id).first()
    if not template:
        return send_error("Plantilla no encontrada")
    db.delete(template)
    db.commit()
    return send_response(None, "Plantilla eliminada")


# ── Assignments ───────────────────────────────────────────────────────────────

@router_assignments.post("")
def assign_form(data: FormAssignRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    template = db.query(FormTemplate).filter(FormTemplate.id == data.form_template_id).first()
    if not template:
        return send_error("Plantilla no encontrada")

    client = db.query(UserDetail).filter(UserDetail.id == data.client_user_detail_id).first()
    if not client:
        return send_error("Cliente no encontrado")

    existing = db.query(FormAssignment).filter(
        FormAssignment.client_user_detail_id == data.client_user_detail_id,
        FormAssignment.status == "pending",
    ).first()
    if existing:
        return send_error("El cliente ya tiene un formulario pendiente")

    assignment = FormAssignment(
        form_template_id=data.form_template_id,
        client_user_detail_id=data.client_user_detail_id,
        assigned_by=current_user.id,
        status="pending",
    )
    db.add(assignment)

    client.status_id = _get_client_state_id(db, "Formulario pendiente")
    db.commit()
    db.refresh(assignment)
    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "Formulario asignado")


@router_assignments.get("/pending")
def pending_assignments(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    assignments = db.query(FormAssignment).filter(
        FormAssignment.assigned_by == current_user.id,
        FormAssignment.status == "pending",
    ).all()
    return send_response([FormAssignmentOut.model_validate(a).model_dump() for a in assignments], "OK")


@router_assignments.get("/client/{client_id}")
def client_assignment(client_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    assignment = db.query(FormAssignment).filter(
        FormAssignment.client_user_detail_id == client_id,
    ).order_by(FormAssignment.created_at.desc()).first()
    if not assignment:
        return send_error("Sin formulario asignado")
    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "OK")


@router_assignments.post("/{id}/submit")
def submit_form(id: str, data: FormSubmitRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    assignment = db.query(FormAssignment).filter(FormAssignment.id == id).first()
    if not assignment:
        return send_error("Formulario no encontrado")
    if assignment.status == "submitted":
        return send_error("Este formulario ya fue enviado")

    db.query(FormResponse).filter(FormResponse.form_assignment_id == id).delete()

    for item in data.responses:
        db.add(FormResponse(
            form_assignment_id=id,
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
    db.refresh(assignment)
    print(f"FORM SUBMITTED: cliente {assignment.client_user_detail_id} envió formulario {id}")
    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "Formulario enviado correctamente")


@router_assignments.get("/{id}/responses")
def get_responses(id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    assignment = db.query(FormAssignment).filter(FormAssignment.id == id).first()
    if not assignment:
        return send_error("Formulario no encontrado")
    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "OK")
