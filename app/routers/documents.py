import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.core.responses import send_response, send_error
from app.core.dependencies import require_role_ids, verify_client_access, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.email import _send
from app.routers.files import _get_r2_client, _public_url
from app.models.document import Document
from app.models.user import User, UserDetail

router = APIRouter(prefix="/documents", tags=["Documents"])


class _SendRequest(BaseModel):
    client_user_detail_id: str

_CATEGORIES = {"contratos", "guias", "plantillas"}
_ALLOWED = {"application/pdf"}
_MAX_MB = 25


def _serialize(d: Document, db: Session | None = None) -> dict:
    client_name = None
    if d.client_user_detail_id and db is not None:
        detail = db.query(UserDetail).filter(UserDetail.id == d.client_user_detail_id).first()
        if detail:
            client_name = f"{detail.name or ''} {detail.last_name or ''}".strip() or None
    return {
        "id": d.id,
        "name": d.name,
        "category": d.category,
        "file_url": d.file_url,
        "size_kb": d.size_kb,
        "content_type": d.content_type,
        "client_user_detail_id": d.client_user_detail_id,
        "client_name": client_name,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.post("", summary="Subir documento", description="Sube un PDF a la librería del coach y guarda su registro. Categoría: contratos/guias/plantillas.")
async def create_document(
    file: UploadFile = File(...),
    category: str = Form("guias"),
    name: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    cat = category if category in _CATEGORIES else "guias"
    if file.content_type not in _ALLOWED:
        return send_error("Solo se permiten archivos PDF.", code=400)
    if not settings.AWS_BUCKET:
        return send_error("Almacenamiento no configurado", code=500)

    content = await file.read()
    if len(content) > _MAX_MB * 1024 * 1024:
        return send_error(f"El archivo supera el límite de {_MAX_MB} MB", code=400)

    key = f"documents/{cat}/{uuid.uuid4()}.pdf"
    try:
        r2 = _get_r2_client()
        r2.put_object(
            Bucket=settings.AWS_BUCKET,
            Key=key,
            Body=content,
            ContentType="application/pdf",
            CacheControl="public, max-age=31536000",
        )
    except Exception as e:
        return send_error(f"Error al subir el archivo: {str(e)}", code=500)

    doc_name = (name or file.filename or "Documento").strip()
    if not doc_name.lower().endswith(".pdf"):
        doc_name = f"{doc_name}.pdf" if not name else doc_name
    doc = Document(
        coach_id=current_user.id,
        name=doc_name,
        category=cat,
        file_url=_public_url(key),
        file_key=key,
        size_kb=round(len(content) / 1024, 1),
        content_type=file.content_type,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return send_response(_serialize(doc), "Documento subido")


@router.get("", summary="Listar documentos", description="Lista los documentos del coach, opcionalmente filtrados por categoría.")
def list_documents(
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(Document).filter(Document.coach_id == current_user.id)
    if category:
        q = q.filter(Document.category == category)
    docs = q.order_by(Document.created_at.desc(), Document.id.desc()).all()
    return send_response([_serialize(d, db) for d in docs], "OK")


@router.post("/{doc_id}/send", summary="Asignar y enviar documento a un cliente", description="Asigna el documento a un cliente del coach y le envía el enlace por email.")
def send_document(
    doc_id: int,
    data: _SendRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.coach_id == current_user.id).first()
    if not doc:
        return send_error("Documento no encontrado", code=404)
    verify_client_access(data.client_user_detail_id, current_user, db)
    detail = db.query(UserDetail).filter(UserDetail.id == data.client_user_detail_id).first()
    if not detail:
        return send_error("Cliente no encontrado", code=404)

    client_email = None
    if detail.user_id:
        user = db.query(User).filter(User.id == detail.user_id).first()
        if user:
            client_email = user.email
    if not client_email:
        return send_error("El cliente no tiene email registrado", code=422)

    # Asignar el documento al cliente
    doc.client_user_detail_id = detail.id
    db.commit()

    client_name = f"{detail.name or ''} {detail.last_name or ''}".strip() or "Cliente"
    coach_name = current_user.name or current_user.email
    html = f"""
<div style="font-family:sans-serif;max-width:560px;margin:auto;padding:32px 24px;">
  <h2 style="color:#4F46E5;margin-bottom:8px;">Alzum.io</h2>
  <p style="color:#374151;font-size:15px;">Hola <strong>{client_name}</strong>,</p>
  <p style="color:#374151;font-size:15px;">Tu entrenador/a <strong>{coach_name}</strong> te ha compartido el siguiente documento:</p>
  <p style="color:#111827;font-size:16px;font-weight:700;margin:20px 0 12px;">{doc.name}</p>
  <p style="margin:0 0 24px;"><a href="{doc.file_url}" style="display:inline-block;background:#4F46E5;color:#fff;text-decoration:none;padding:11px 22px;border-radius:9px;font-size:14px;font-weight:700;">Ver documento (PDF)</a></p>
  <hr style="border:none;border-top:1px solid #E5E7EB;margin:24px 0;"/>
  <p style="color:#9CA3AF;font-size:12px;text-align:center;">Alzum.io — Gestión de coaching deportivo</p>
</div>"""
    ok, msg = _send(client_email, f"{doc.name} — {coach_name}", html)
    if not ok:
        return send_error(f"Documento asignado, pero el email falló: {msg}", code=502)
    return send_response(_serialize(doc, db), "Documento enviado")


@router.delete("/{doc_id}", summary="Eliminar documento", description="Elimina un documento del coach y su archivo en el almacenamiento.")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.coach_id == current_user.id).first()
    if not doc:
        return send_error("Documento no encontrado", code=404)
    if doc.file_key and settings.AWS_BUCKET:
        try:
            _get_r2_client().delete_object(Bucket=settings.AWS_BUCKET, Key=doc.file_key)
        except Exception:
            pass
    db.delete(doc)
    db.commit()
    return send_response(None, "Documento eliminado")
