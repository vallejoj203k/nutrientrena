"""
Contratos y plantillas de contratos.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.contract import Contract, ContractTemplate
from app.models.user import User, UserDetail
from app.core.dependencies import require_role_ids, get_current_user, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.pdf.contract_pdf import generate_contract_pdf

router = APIRouter(prefix="/contracts", tags=["Contracts"])

ALLOWED = (SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)

DEFAULT_TEMPLATE_TITLE = "Contrato de Servicios de Entrenamiento Personal"
DEFAULT_TEMPLATE_CONTENT = """CONTRATO DE SERVICIOS DE ENTRENAMIENTO PERSONAL

Entre {{coach_nombre}} (el/la Entrenador/a) y {{nombre_cliente}} (el/la Cliente), se acuerda lo siguiente:

1. OBJETO DEL CONTRATO
El/la Entrenador/a prestará servicios de entrenamiento personal y asesoramiento nutricional personalizado al/la Cliente, en los términos que se establecen en el presente contrato.

2. SERVICIOS CONTRATADOS
{{servicio}}

3. DURACIÓN
El presente contrato tendrá una vigencia de {{duracion}}, comenzando en la fecha indicada al pie de este documento.

4. PRECIO Y FORMA DE PAGO
El precio acordado por los servicios descritos es de {{precio}}.
El pago se realizará según lo pactado entre ambas partes.

5. COMPROMISOS DEL CLIENTE
- Asistir puntualmente a las sesiones acordadas.
- Seguir las recomendaciones del/la Entrenador/a dentro de sus posibilidades.
- Informar de cualquier condición médica, lesión o circunstancia relevante que pueda afectar al entrenamiento.
- No compartir los materiales y programas proporcionados con terceros.

6. COMPROMISOS DEL ENTRENADOR/A
- Diseñar y adaptar los planes de entrenamiento según las necesidades del/la Cliente.
- Mantener la confidencialidad de los datos personales y de salud del/la Cliente.
- Estar disponible para resolver dudas dentro del horario acordado.

7. CANCELACIÓN Y REEMBOLSO
Las sesiones canceladas con menos de 24 horas de antelación no serán reembolsadas, salvo causa mayor debidamente justificada.

8. CONFIDENCIALIDAD
Toda la información compartida entre las partes —incluyendo datos de salud, objetivos y resultados— se tratará con total confidencialidad y no será divulgada a terceros sin consentimiento expreso.

9. CONSENTIMIENTO
El/la Cliente declara estar en condiciones físicas adecuadas para realizar actividad física y exime al/la Entrenador/a de responsabilidades derivadas del incumplimiento de las recomendaciones recibidas.

10. LEGISLACIÓN APLICABLE
El presente contrato se rige por la legislación vigente en el país de prestación de los servicios. Cualquier controversia será resuelta mediante acuerdo amistoso o, en su defecto, ante los tribunales competentes.

FIRMA Y CONFORMIDAD

Fecha: {{fecha}}

__________________________          __________________________
{{coach_nombre}}                    {{nombre_cliente}}
Entrenador/a Personal               Cliente
"""

INFORMED_CONSENT_CONTENT = """CONSENTIMIENTO INFORMADO PARA ACTIVIDAD FÍSICA Y ENTRENAMIENTO PERSONAL

Yo, {{nombre_cliente}}, declaro haber sido informado/a por {{coach_nombre}} sobre los riesgos inherentes a la práctica de actividad física intensa y manifiesto mi consentimiento libre y voluntario para participar en los programas de entrenamiento diseñados por el/la profesional mencionado/a.

DECLARACIÓN DE SALUD
Declaro que:
- No padezco ninguna enfermedad cardiovascular, respiratoria o musculoesquelética que contraindique la práctica de ejercicio físico, salvo las informadas expresamente al entrenador/a.
- Me comprometo a informar de inmediato cualquier cambio en mi estado de salud.
- He sido informado/a de que en caso de sentir dolor, mareo, dificultad respiratoria o cualquier malestar durante el entrenamiento, debo detener la actividad y comunicarlo al entrenador/a.

RIESGOS ASUMIDOS
Entiendo que la práctica de ejercicio físico conlleva ciertos riesgos como fatiga muscular, agujetas, y en casos excepcionales, lesiones. Al firmar este documento, asumo dichos riesgos de manera voluntaria e informada.

DATOS DE CONTACTO DE EMERGENCIA
Nombre: {{contacto_emergencia}}
Teléfono: {{telefono_emergencia}}

AUTORIZACIÓN FOTOGRÁFICA (opcional)
Autorizo / No autorizo el uso de imágenes o vídeos de mi progreso con fines demostrativos, siempre de forma anónima y sin revelar datos personales.

Fecha: {{fecha}}

__________________________          __________________________
{{coach_nombre}}                    {{nombre_cliente}}
Entrenador/a Personal               Cliente
"""


def _ensure_default_templates(db: Session, coach_id: int):
    """Crea las plantillas por defecto si el coach no tiene ninguna."""
    count = db.query(ContractTemplate).filter_by(coach_id=coach_id).count()
    if count == 0:
        defaults = [
            ContractTemplate(
                coach_id=coach_id,
                title="Contrato de Servicios de Entrenamiento Personal",
                type="servicio",
                content=DEFAULT_TEMPLATE_CONTENT,
            ),
            ContractTemplate(
                coach_id=coach_id,
                title="Consentimiento Informado",
                type="consentimiento",
                content=INFORMED_CONSENT_CONTENT,
            ),
        ]
        db.add_all(defaults)
        db.commit()


def _serialize_template(t: ContractTemplate) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "type": t.type,
        "content": t.content,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_contract(c: Contract) -> dict:
    client_name = None
    if c.client:
        client_name = f"{c.client.name or ''} {c.client.last_name or ''}".strip() or None
    return {
        "id": c.id,
        "title": c.title,
        "type": c.type,
        "status": c.status,
        "content": c.content,
        "client_id": c.client_id,
        "client_name": client_name,
        "template_id": c.template_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


# ── Templates ─────────────────────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    title: str
    type: str = "servicio"
    content: str


class TemplateUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None


@router.get("/templates")
def list_templates(
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    _ensure_default_templates(db, current_user.id)
    templates = db.query(ContractTemplate).filter_by(coach_id=current_user.id).order_by(ContractTemplate.created_at).all()
    return send_response([_serialize_template(t) for t in templates], "ok")


@router.post("/templates")
def create_template(
    data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    t = ContractTemplate(coach_id=current_user.id, title=data.title, type=data.type, content=data.content)
    db.add(t)
    db.commit()
    db.refresh(t)
    return send_response(_serialize_template(t), "Plantilla creada")


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    t = db.query(ContractTemplate).filter_by(id=template_id, coach_id=current_user.id).first()
    if not t:
        return send_error("Plantilla no encontrada", code=404)
    if data.title is not None:
        t.title = data.title
    if data.type is not None:
        t.type = data.type
    if data.content is not None:
        t.content = data.content
    db.commit()
    db.refresh(t)
    return send_response(_serialize_template(t), "Plantilla actualizada")


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    t = db.query(ContractTemplate).filter_by(id=template_id, coach_id=current_user.id).first()
    if not t:
        return send_error("Plantilla no encontrada", code=404)
    db.delete(t)
    db.commit()
    return send_response({"id": template_id}, "Plantilla eliminada")


# ── Contracts ─────────────────────────────────────────────────────────────────

class ContractCreate(BaseModel):
    title: str
    type: str = "servicio"
    content: str
    client_id: Optional[int] = None
    template_id: Optional[int] = None
    status: str = "borrador"


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    client_id: Optional[int] = None
    status: Optional[str] = None


@router.get("")
def list_contracts(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    q = db.query(Contract).options(
        joinedload(Contract.client),
    ).filter_by(coach_id=current_user.id)
    if status:
        q = q.filter(Contract.status == status)
    contracts = q.order_by(Contract.created_at.desc()).all()
    return send_response([_serialize_contract(c) for c in contracts], "ok")


@router.post("")
def create_contract(
    data: ContractCreate,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    c = Contract(
        coach_id=current_user.id,
        title=data.title,
        type=data.type,
        content=data.content,
        client_id=data.client_id,
        template_id=data.template_id,
        status=data.status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    db.refresh(c, ["client"])
    return send_response(_serialize_contract(c), "Contrato creado")


@router.get("/{contract_id}")
def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    c = db.query(Contract).options(joinedload(Contract.client)).filter_by(
        id=contract_id, coach_id=current_user.id
    ).first()
    if not c:
        return send_error("Contrato no encontrado", code=404)
    return send_response(_serialize_contract(c), "ok")


@router.put("/{contract_id}")
def update_contract(
    contract_id: int,
    data: ContractUpdate,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    c = db.query(Contract).options(joinedload(Contract.client)).filter_by(
        id=contract_id, coach_id=current_user.id
    ).first()
    if not c:
        return send_error("Contrato no encontrado", code=404)
    if data.title is not None:
        c.title = data.title
    if data.type is not None:
        c.type = data.type
    if data.content is not None:
        c.content = data.content
    if data.client_id is not None:
        c.client_id = data.client_id
    if data.status is not None:
        c.status = data.status
    db.commit()
    db.refresh(c)
    db.refresh(c, ["client"])
    return send_response(_serialize_contract(c), "Contrato actualizado")


@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    c = db.query(Contract).filter_by(id=contract_id, coach_id=current_user.id).first()
    if not c:
        return send_error("Contrato no encontrado", code=404)
    db.delete(c)
    db.commit()
    return send_response({"id": contract_id}, "Contrato eliminado")


@router.get("/{contract_id}/pdf")
def download_contract_pdf(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    c = db.query(Contract).options(joinedload(Contract.client)).filter_by(
        id=contract_id, coach_id=current_user.id
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    pdf_bytes = generate_contract_pdf(c)
    filename = f"contrato_{contract_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{contract_id}/send")
def send_contract(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
    db: Session = Depends(get_db),
):
    c = db.query(Contract).options(joinedload(Contract.client)).filter_by(
        id=contract_id, coach_id=current_user.id
    ).first()
    if not c:
        return send_error("Contrato no encontrado", code=404)

    client_email = None
    if c.client and c.client.user_id:
        user = db.query(User).filter_by(id=c.client.user_id).first()
        if user:
            client_email = user.email

    if not client_email:
        return send_error("El cliente no tiene email registrado", code=422)

    try:
        import resend
        from app.config import settings
        resend.api_key = settings.RESEND_API_KEY

        pdf_bytes = generate_contract_pdf(c)
        import base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode()

        coach_name = current_user.name or current_user.email
        client_name = f"{c.client.name or ''} {c.client.last_name or ''}".strip() or "Cliente"

        resend.Emails.send({
            "from": "Alzum.io <noreply@alzum.io>",
            "to": [client_email],
            "subject": f"{c.title} — {coach_name}",
            "html": f"""
<div style="font-family:sans-serif;max-width:560px;margin:auto;padding:32px 24px;">
  <h2 style="color:#4F46E5;margin-bottom:8px;">Alzum.io</h2>
  <p style="color:#374151;font-size:15px;">Hola <strong>{client_name}</strong>,</p>
  <p style="color:#374151;font-size:15px;">Tu entrenador/a <strong>{coach_name}</strong> te ha enviado el siguiente documento:</p>
  <p style="color:#111827;font-size:16px;font-weight:700;margin:20px 0 4px;">{c.title}</p>
  <p style="color:#6B7280;font-size:13px;margin-bottom:24px;">Encontrarás el documento adjunto en formato PDF.</p>
  <hr style="border:none;border-top:1px solid #E5E7EB;margin:24px 0;"/>
  <p style="color:#9CA3AF;font-size:12px;text-align:center;">Alzum.io — Gestión de coaching deportivo</p>
</div>""",
            "attachments": [{"filename": f"contrato_{c.id}.pdf", "content": pdf_b64}],
        })

        c.status = "enviado"
        db.commit()
        return send_response({"email_sent": True, "to": client_email}, "Contrato enviado por email")
    except Exception as e:
        return send_error(f"Error al enviar email: {str(e)}", code=500)
