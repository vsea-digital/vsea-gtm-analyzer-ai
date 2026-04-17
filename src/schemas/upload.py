from pydantic import BaseModel


class UploadResponse(BaseModel):
    request_id: str
    gcs_uri: str
    filename: str
    mime_type: str
    size_bytes: int
