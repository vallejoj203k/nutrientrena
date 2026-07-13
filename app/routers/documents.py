import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.core.responses import send_response, send_error
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.routers.files import _get_r2_client, _public_url
from app.models.document import Document

router = APIRouter(prefix="/documents", tags=["Documents"])

_CATEGORIES = {"contratos", "guias", "plantillas"}
_ALLOWED = {"application/pdf"}
_MAX_MB = 25


def _serialize(d: Document) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "category": d.category,
        "file_url": d.file_url,
        "size_kb": d.size_kb,
        "content_type": d.content_type,
        "client_user_detail_id": d.client_user_detail_id,
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
    return send_response([_serialize(d) for d in docs], "OK")


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
