import os

import pytest


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    import src.configs.config as cfg_module
    import src.services.gcs.client as gcs_module

    cfg_module._config = None
    gcs_module._client = None
    yield
    cfg_module._config = None
    gcs_module._client = None


@pytest.fixture
def set_env(monkeypatch):
    def _apply(**kwargs):
        for k, v in kwargs.items():
            monkeypatch.setenv(k, v)

    return _apply


@pytest.fixture
def valid_brief() -> dict:
    return {
        "companyName": "Acme",
        "product": "Widget",
        "gtmScore": 72,
        "structuralBlocker": False,
        "blockerExplanation": "",
        "verdict": "Conditional Go",
        "verdictReason": "Strong fit",
        "summary": "Go for it",
        "scoreBreakdown": [
            {
                "dimension": "Market Size & Tailwind",
                "score": 15,
                "max": 20,
                "note": "ok",
                "blocker": False,
            },
            {
                "dimension": "Regulatory Feasibility",
                "score": 14,
                "max": 20,
                "note": "ok",
                "blocker": False,
            },
            {
                "dimension": "Competitive Intensity",
                "score": 10,
                "max": 15,
                "note": "ok",
                "blocker": False,
            },
            {
                "dimension": "Entry Barrier Realism",
                "score": 10,
                "max": 15,
                "note": "ok",
                "blocker": False,
            },
            {
                "dimension": "Timing Alignment",
                "score": 10,
                "max": 15,
                "note": "ok",
                "blocker": False,
            },
            {
                "dimension": "GTM Execution Clarity",
                "score": 7,
                "max": 10,
                "note": "ok",
                "blocker": False,
            },
            {
                "dimension": "Company-Market Readiness",
                "score": 3,
                "max": 5,
                "note": "ok",
                "blocker": False,
            },
        ],
        "marketOpportunity": {
            "headline": "Big market",
            "narrative": "Growing fast",
            "keyStats": ["TAM $10B", "Users 100M"],
        },
        "marketSizing": {
            "tam": {
                "label": "Total Addressable Market",
                "value": "$10B",
                "pct": 85,
                "note": "ok",
            },
            "sam": {
                "label": "Serviceable Addressable Market",
                "value": "$3B",
                "pct": 55,
                "note": "ok",
            },
            "som": {
                "label": "Serviceable Obtainable Market",
                "value": "$500M",
                "pct": 22,
                "note": "ok",
            },
            "cagr": "20%",
            "growth": "fast",
        },
        "marketAnalysis": {
            "overview": "good",
            "trends": ["a", "b", "c"],
            "risks": ["x", "y"],
        },
        "opportunities": [
            {"title": "A", "desc": "a"},
            {"title": "B", "desc": "b"},
        ],
        "competitors": [
            {
                "rank": 1,
                "name": "A",
                "hq": "SG",
                "desc": "a",
                "threat": "High",
                "weakness": "x",
            },
            {
                "rank": 2,
                "name": "B",
                "hq": "ID",
                "desc": "b",
                "threat": "Medium",
                "weakness": "y",
            },
            {
                "rank": 3,
                "name": "C",
                "hq": "MY",
                "desc": "c",
                "threat": "Low",
                "weakness": "z",
            },
        ],
        "regulatory": [
            {
                "level": "critical",
                "agency": "MAS",
                "title": "T1",
                "desc": "d",
                "blocker": False,
            },
            {
                "level": "medium",
                "agency": "OJK",
                "title": "T2",
                "desc": "d",
                "blocker": False,
            },
            {
                "level": "low",
                "agency": "X",
                "title": "T3",
                "desc": "d",
                "blocker": False,
            },
        ],
        "gtmPlan": {
            "phase1": {
                "timing": "Month 1-3",
                "title": "P1",
                "items": ["a", "b", "c"],
            },
            "phase2": {
                "timing": "Month 4-9",
                "title": "P2",
                "items": ["a", "b", "c"],
            },
            "phase3": {
                "timing": "Month 10-18",
                "title": "P3",
                "items": ["a", "b", "c"],
            },
        },
    }


os.environ.setdefault("SERVICE_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")
os.environ.setdefault("GCS_BUCKET_NAME", "test-bucket")
