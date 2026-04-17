from fastapi.testclient import TestClient

import src.routes.upload.route as upload_route
from main import app


def test_upload_rejects_missing_key():
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/upload",
            files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert resp.status_code == 401


def test_upload_ok(monkeypatch):
    monkeypatch.setattr(
        upload_route,
        "upload_bytes",
        lambda name, data, ct: f"gs://test-bucket/{name}",
    )

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/upload",
            headers={"X-API-Key": "test-key"},
            files={"file": ("pitch.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["filename"] == "pitch.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["size_bytes"] == len(b"%PDF-1.4 fake")
    assert body["gcs_uri"].startswith("gs://test-bucket/gtm-uploads/")
    assert body["gcs_uri"].endswith("/pitch.pdf")


def test_upload_rejects_bad_extension(monkeypatch):
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/upload",
            headers={"X-API-Key": "test-key"},
            files={"file": ("x.exe", b"bin", "application/octet-stream")},
        )
    assert resp.status_code == 415
