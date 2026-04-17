from __future__ import annotations

from google.cloud import storage

from src.configs.config import get_config
from src.logging.custom_logger import Logging

LOGGER = Logging().get_logger("gcs_client")

_client: storage.Client | None = None


def get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    without_scheme = gcs_uri[len("gs://") :]
    bucket, _, blob_name = without_scheme.partition("/")
    if not bucket or not blob_name:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    return bucket, blob_name


def upload_bytes(blob_name: str, data: bytes, content_type: str) -> str:
    """Upload raw bytes to the configured bucket. Returns gs:// URI."""
    bucket_name = get_config().secrets.GCS_BUCKET_NAME
    if not bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME is not configured")

    bucket = get_client().bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=content_type)

    gcs_uri = f"gs://{bucket_name}/{blob_name}"
    LOGGER.info(f"Uploaded {len(data)} bytes to {gcs_uri}")
    return gcs_uri


def download_bytes(gcs_uri: str) -> bytes:
    bucket_name, blob_name = parse_gcs_uri(gcs_uri)
    bucket = get_client().bucket(bucket_name)
    blob = bucket.blob(blob_name)
    data = blob.download_as_bytes()
    LOGGER.info(f"Downloaded {len(data)} bytes from {gcs_uri}")
    return data


def delete_object(gcs_uri: str) -> None:
    """Best-effort delete. Logs but never raises."""
    try:
        bucket_name, blob_name = parse_gcs_uri(gcs_uri)
        bucket = get_client().bucket(bucket_name)
        bucket.blob(blob_name).delete()
        LOGGER.info(f"Deleted {gcs_uri}")
    except Exception as e:  # noqa: BLE001
        LOGGER.warning(f"Failed to delete {gcs_uri}: {e}")
