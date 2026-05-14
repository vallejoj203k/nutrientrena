from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
import boto3
import uuid

from app.config import settings
from app.core.responses import send_response, send_error

router = APIRouter(prefix="/files", tags=["Files"])


def _get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION,
    )


@router.post("/external")
async def upload_file(file: UploadFile = File(...), folder: Optional[str] = Form("uploads")):
    if not settings.AWS_BUCKET:
        return send_error("AWS no configurado", code=500)
    s3 = _get_s3_client()
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    key = f"{folder}/{uuid.uuid4()}.{ext}"
    content = await file.read()
    s3.put_object(Bucket=settings.AWS_BUCKET, Key=key, Body=content, ContentType=file.content_type)
    url = f"https://{settings.AWS_BUCKET}.s3.{settings.AWS_DEFAULT_REGION}.amazonaws.com/{key}"
    return send_response({"url": url, "key": key}, "Archivo subido")


@router.get("/external")
def list_files(folder: Optional[str] = "uploads"):
    if not settings.AWS_BUCKET:
        return send_error("AWS no configurado", code=500)
    s3 = _get_s3_client()
    response = s3.list_objects_v2(Bucket=settings.AWS_BUCKET, Prefix=folder)
    files = [obj["Key"] for obj in response.get("Contents", [])]
    return send_response({"files": files}, "OK")


@router.post("/delete")
def delete_file(key: str = Form(...)):
    if not settings.AWS_BUCKET:
        return send_error("AWS no configurado", code=500)
    s3 = _get_s3_client()
    s3.delete_object(Bucket=settings.AWS_BUCKET, Key=key)
    return send_response({"key": key}, "Archivo eliminado")
