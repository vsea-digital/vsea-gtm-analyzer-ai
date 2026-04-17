import json

from fastapi.testclient import TestClient

import src.routes.analyze_doc.route as doc_route
import src.routes.analyze_url.route as url_route
from main import app


def test_analyze_document_flow(monkeypatch, valid_brief):
    monkeypatch.setattr(doc_route, "download_bytes", lambda uri: b"%PDF-1.4 fake")
    monkeypatch.setattr(doc_route, "delete_object", lambda uri: None)

    async def fake_runner(agent, parts):
        return json.dumps(valid_brief)

    monkeypatch.setattr(doc_route, "run_agent_once", fake_runner)
    monkeypatch.setattr(doc_route, "create_document_agent", lambda m, i: object())

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/analyze/document",
            headers={"X-API-Key": "test-key"},
            json={
                "gcs_uri": "gs://test-bucket/gtm-uploads/abc/pitch.pdf",
                "market": "Indonesia",
                "industry": "Fintech",
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["companyName"] == "Acme"
    assert body["verdict"] == "Go"
    assert len(body["scoreBreakdown"]) == 6


def test_analyze_document_rejects_unsupported_type(monkeypatch):
    monkeypatch.setattr(doc_route, "download_bytes", lambda uri: b"x")
    monkeypatch.setattr(doc_route, "delete_object", lambda uri: None)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/analyze/document",
            headers={"X-API-Key": "test-key"},
            json={
                "gcs_uri": "gs://test-bucket/gtm-uploads/abc/old.ppt",
                "market": "Indonesia",
                "industry": "Fintech",
            },
        )

    assert resp.status_code == 415


def test_analyze_url_flow(monkeypatch, valid_brief):
    async def fake_runner(agent, parts):
        return json.dumps(valid_brief)

    monkeypatch.setattr(url_route, "run_agent_once", fake_runner)
    monkeypatch.setattr(url_route, "create_research_agent", lambda m, i: object())

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/analyze/url",
            headers={"X-API-Key": "test-key"},
            json={
                "url": "https://example.com",
                "market": "Indonesia",
                "industry": "Fintech",
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["gtmScore"] == 72


def test_analyze_url_requires_auth():
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/analyze/url",
            json={"url": "https://example.com", "market": "ID", "industry": "Fintech"},
        )
    assert resp.status_code == 401
