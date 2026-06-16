from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Optional
import boto3
import uuid

from app.config import settings
from app.core.responses import send_response, send_error
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH

router = APIRouter(prefix="/files", tags=["Files"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_MB = 10


def _get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url="https://77925e3b1a6f6513bce155f71f6aa790.r2.cloudflarestorage.com",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def _public_url(key: str) -> str:
    base = (settings.R2_PUBLIC_URL or "").rstrip("/")
    return f"{base}/{key}"


@router.post("/upload", summary="Subir archivo", description="Sube una imagen a Cloudflare R2. Formatos: JPG, PNG, WEBP, GIF. Máximo 10 MB.")
async def upload_file(
    file: UploadFile = File(...),
    folder: Optional[str] = Form("uploads"),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    """
    Sube una imagen a Cloudflare R2 y devuelve la URL pública.
    - Carpetas disponibles: uploads, profiles, checkins, aliments
    - Formatos: JPG, PNG, WEBP, GIF
    - Tamaño máximo: 5 MB
    """
    if not settings.AWS_BUCKET:
        return send_error("Almacenamiento no configurado", code=500)

    if file.content_type not in ALLOWED_TYPES:
        return send_error(
            f"Tipo de archivo no permitido. Usa: {', '.join(ALLOWED_TYPES)}", code=400
        )

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        return send_error(f"El archivo supera el límite de {MAX_SIZE_MB} MB", code=400)

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    key = f"{folder}/{uuid.uuid4()}.{ext}"

    try:
        r2 = _get_r2_client()
        r2.put_object(
            Bucket=settings.AWS_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type,
            CacheControl="public, max-age=31536000",
        )
    except Exception as e:
        return send_error(f"Error al subir el archivo: {str(e)}", code=500)

    url = _public_url(key)
    return send_response(
        {
            "url": url,
            "key": key,
            "size_kb": round(len(content) / 1024, 1),
            "content_type": file.content_type,
        },
        "Archivo subido correctamente",
    )


@router.delete("/delete", summary="Eliminar archivo", description="Elimina un archivo de Cloudflare R2 usando su key.")
def delete_file(key: str, _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    """Elimina un archivo de R2 por su key."""
    if not settings.AWS_BUCKET:
        return send_error("Almacenamiento no configurado", code=500)
    try:
        r2 = _get_r2_client()
        r2.delete_object(Bucket=settings.AWS_BUCKET, Key=key)
    except Exception as e:
        return send_error(f"Error al eliminar: {str(e)}", code=500)
    return send_response({"key": key}, "Archivo eliminado")


@router.get("/list", summary="Listar archivos", description="Lista todos los archivos de una carpeta en el bucket de Cloudflare R2.")
def list_files(folder: str = "uploads", _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    """Lista los archivos de una carpeta en R2."""
    if not settings.AWS_BUCKET:
        return send_error("Almacenamiento no configurado", code=500)
    try:
        r2 = _get_r2_client()
        response = r2.list_objects_v2(Bucket=settings.AWS_BUCKET, Prefix=folder)
        files = [
            {"key": obj["Key"], "url": _public_url(obj["Key"]), "size_kb": round(obj["Size"] / 1024, 1)}
            for obj in response.get("Contents", [])
        ]
    except Exception as e:
        return send_error(f"Error al listar: {str(e)}", code=500)
    return send_response({"files": files, "total": len(files)}, "ok")
