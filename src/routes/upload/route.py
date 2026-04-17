from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.configs.config import get_config
from src.logging.custom_logger import Logging
from src.middlewares.auth import verify_service_key
from src.schemas.upload import UploadResponse
from src.services.gcs.client import upload_bytes

LOGGER = Logging().get_logger("upload_route")

router = APIRouter(prefix="/upload", tags=["upload"])

_ACCEPTED_MIME = {
    "application/pdf": ".pdf",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
}

_ACCEPTED_EXT = {".pdf", ".ppt", ".pptx"}


def _sniff_mime(filename: str, declared: str) -> str:
    if declared in _ACCEPTED_MIME:
        return declared
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".pptx"):
        return (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    if lower.endswith(".ppt"):
        return "application/vnd.ms-powerpoint"
    raise HTTPException(status_code=415, detail=f"Unsupported file type: {declared}")


@router.post("", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    _: str = Depends(verify_service_key),
) -> UploadResponse:
    config = get_config()

    filename = file.filename or "upload.bin"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if (
        ext
        and ext not in _ACCEPTED_EXT
        and (file.content_type or "") not in _ACCEPTED_MIME
    ):
        raise HTTPException(
            status_code=415, detail=f"Unsupported file extension: {ext}"
        )

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > config.upload.max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(data)} bytes (limit {config.upload.max_bytes})",
        )

    mime_type = _sniff_mime(filename, file.content_type or "")

    request_id = uuid.uuid4().hex
    blob_name = f"{config.gcs.upload_prefix}{request_id}/{filename}"

    try:
        gcs_uri = upload_bytes(blob_name, data, mime_type)
    except Exception as e:  # noqa: BLE001
        LOGGER.error(f"GCS upload failed: {e}")
        raise HTTPException(status_code=502, detail=f"Upload to GCS failed: {e}")

    return UploadResponse(
        request_id=request_id,
        gcs_uri=gcs_uri,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(data),
    )
