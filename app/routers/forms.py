from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.core.email import notify_coach_form_submitted, send_form_link_email
from app.config import settings
from app.models.form import FormTemplate, FormTemplateField, FormAssignment, FormResponse, PROFILE_FIELD_MAP
from app.models.user import UserDetail, UserParent, User
from app.models.parameter import ParameterDetail
from app.schemas.form import (
    FormTemplateCreate, FormTemplateUpdate, FormTemplateOut,
    FormAssignRequest, FormSubmitRequest, FormAssignmentOut,
)
from app.seeds.default_form import update_default_form


def _get_coach_for_client(client_detail_id: str, db: Session):
    """Return (coach_detail, coach_user) for a client, or (None, None)."""
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


# ── Maintenance ───────────────────────────────────────────────────────────────

@router_templates.post("/update-default", summary="Actualizar plantilla por defecto", description="Operación idempotente que agrega campos faltantes a la plantilla de intake por defecto.")
def update_default_template(
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN)),
):
    """Idempotent: append any missing fields to the default intake template."""
    update_default_form(db)
    template = db.query(FormTemplate).filter(FormTemplate.is_default.is_(True)).first()
    if not template:
        return send_error("No hay plantilla por defecto")
    return send_response(FormTemplateOut.model_validate(template).model_dump(), "Plantilla actualizada")


# ── Templates ─────────────────────────────────────────────────────────────────

@router_templates.post("", summary="Crear plantilla de formulario", description="Crea una nueva plantilla de formulario con campos personalizados.")
def create_template(data: FormTemplateCreate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    if data.is_default:
        db.query(FormTemplate).filter(
            FormTemplate.created_by == current_user.id,
            FormTemplate.is_default.is_(True),
        ).update({"is_default": False})

    template = FormTemplate(
        title=data.title,
        description=data.description,
        category=data.category or "checkin",
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


@router_templates.get("/default", summary="Plantilla por defecto", description="Retorna la plantilla marcada como predeterminada para nuevos clientes.")
def get_default(db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    template = db.query(FormTemplate).filter(
        FormTemplate.is_default.is_(True),
    ).first()
    if not template:
        return send_error("No hay plantilla por defecto")
    return send_response(FormTemplateOut.model_validate(template).model_dump(), "OK")


@router_templates.get("", summary="Listar plantillas", description="Retorna las plantillas de formulario creadas por el usuario autenticado. Se puede filtrar por categoría (checkin|onboarding|survey).")
def list_templates(category: str | None = None, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    query = db.query(FormTemplate).filter(FormTemplate.created_by == current_user.id)
    if category:
        query = query.filter(FormTemplate.category == category)
    templates = query.all()
    return send_response([FormTemplateOut.model_validate(t).model_dump() for t in templates], "OK")


@router_templates.get("/{id}", summary="Ver plantilla", description="Retorna el detalle de una plantilla con todos sus campos.")
def get_template(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    template = db.query(FormTemplate).filter(FormTemplate.id == id).first()
    if not template:
        return send_error("Plantilla no encontrada")
    return send_response(FormTemplateOut.model_validate(template).model_dump(), "OK")


@router_templates.put("/{id}", summary="Actualizar plantilla", description="Modifica una plantilla de formulario y reemplaza sus campos.")
def update_template(id: int, data: FormTemplateUpdate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    template = db.query(FormTemplate).filter(FormTemplate.id == id).first()
    if not template:
        return send_error("Plantilla no encontrada")

    if data.title is not None:
        template.title = data.title
    if data.description is not None:
        template.description = data.description
    if data.category is not None:
        template.category = data.category
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


@router_templates.delete("/{id}", summary="Eliminar plantilla", description="Elimina una plantilla de formulario por su ID.")
def delete_template(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    template = db.query(FormTemplate).filter(FormTemplate.id == id).first()
    if not template:
        return send_error("Plantilla no encontrada")
    db.delete(template)
    db.commit()
    return send_response(None, "Plantilla eliminada")


# ── Assignments ───────────────────────────────────────────────────────────────

@router_assignments.post("", summary="Asignar formulario a cliente", description="Asigna una plantilla de formulario a un cliente y envía el enlace por email.")
def assign_form(data: FormAssignRequest, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
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

    # Send public form link to client
    client_user = db.query(User).filter(User.id == client.user_id).first()
    if client_user and client_user.email:
        form_link = f"{settings.FRONTEND_URL}/app/public/form.html?id={assignment.id}"
        client_name = f"{client.name or ''} {client.last_name or ''}".strip() or ""
        coach_detail = db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
        coach_name = f"{coach_detail.name or ''} {coach_detail.last_name or ''}".strip() if coach_detail else ""
        send_form_link_email(
            to=client_user.email,
            client_name=client_name,
            form_link=form_link,
            coach_name=coach_name,
        )

    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "Formulario asignado")


@router_assignments.get("/pending-count", summary="Conteo de formularios pendientes", description="Retorna el número de formularios pendientes de respuesta asignados por el usuario.")
def pending_count(db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    count = db.query(FormAssignment).filter(
        FormAssignment.assigned_by == current_user.id,
        FormAssignment.status == "pending",
    ).count()
    return send_response({"count": count}, "OK")


@router_assignments.get("/pending", summary="Formularios pendientes", description="Lista todos los formularios pendientes de respuesta asignados por el usuario.")
def pending_assignments(db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    assignments = db.query(FormAssignment).filter(
        FormAssignment.assigned_by == current_user.id,
        FormAssignment.status == "pending",
    ).all()
    return send_response([FormAssignmentOut.model_validate(a).model_dump() for a in assignments], "OK")


@router_assignments.get("/client/{client_id}", summary="Formulario del cliente", description="Retorna el formulario más reciente asignado a un cliente.")
def client_assignment(client_id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    assignment = db.query(FormAssignment).filter(
        FormAssignment.client_user_detail_id == client_id,
    ).order_by(FormAssignment.created_at.desc()).first()
    if not assignment:
        return send_error("Sin formulario asignado")
    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "OK")


@router_assignments.post("/{id}/submit", summary="Enviar respuestas del formulario", description="Guarda las respuestas y actualiza el perfil del cliente con los datos del formulario.")
def submit_form(id: str, data: FormSubmitRequest, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
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

    # ── Notify coach ──────────────────────────────────────────────────────────
    if client:
        coach_detail, coach_user = _get_coach_for_client(client.id, db)
        if coach_user and coach_user.email:
            client_name = f"{client.name or ''} {client.last_name or ''}".strip() or "Cliente"
            coach_name  = f"{coach_detail.name or ''} {coach_detail.last_name or ''}".strip() or "Coach"
            client_user = db.query(User).filter(User.id == client.user_id).first()
            notify_coach_form_submitted(
                coach_email=coach_user.email,
                coach_name=coach_name,
                client_name=client_name,
                client_email=client_user.email if client_user else "",
            )

    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "Formulario enviado correctamente")


@router_assignments.get("/{id}/responses", summary="Ver respuestas del formulario", description="Retorna el formulario con todas las respuestas enviadas por el cliente.")
def get_responses(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    assignment = db.query(FormAssignment).filter(FormAssignment.id == id).first()
    if not assignment:
        return send_error("Formulario no encontrado")
    return send_response(FormAssignmentOut.model_validate(assignment).model_dump(), "OK")


@router_assignments.get("", summary="Listar todas las asignaciones", description="Retorna todas las asignaciones de formularios del coach autenticado, con nombre del cliente.")
def list_assignments(
    status: Optional[str] = Query(None, description="Filtrar por estado: pending | submitted"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(FormAssignment).filter(FormAssignment.assigned_by == current_user.id)
    if status:
        q = q.filter(FormAssignment.status == status)
    assignments = q.order_by(FormAssignment.created_at.desc()).all()

    result = []
    for a in assignments:
        item = FormAssignmentOut.model_validate(a).model_dump()
        client = db.query(UserDetail).filter(UserDetail.id == a.client_user_detail_id).first()
        if client:
            item["client_name"] = f"{client.name or ''} {client.last_name or ''}".strip() or "Sin nombre"
            client_user = db.query(User).filter(User.id == client.user_id).first()
            item["client_email"] = client_user.email if client_user else ""
        else:
            item["client_name"] = "Cliente"
            item["client_email"] = ""
        result.append(item)

    return send_response(result, "OK")
