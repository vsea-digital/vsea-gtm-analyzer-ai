import json

import pytest

from src.services.agent_runner import parse_gtm_json


def test_parse_plain_json():
    payload = {"companyName": "Acme", "gtmScore": 50}
    assert parse_gtm_json(json.dumps(payload)) == payload


def test_parse_with_markdown_fences():
    text = '```json\n{"companyName":"Acme"}\n```'
    assert parse_gtm_json(text) == {"companyName": "Acme"}


def test_parse_with_surrounding_prose():
    text = 'Sure, here you go:\n{"companyName":"Acme","gtmScore":10}\nLet me know if you need more.'
    assert parse_gtm_json(text) == {"companyName": "Acme", "gtmScore": 10}


def test_parse_unparseable_raises():
    with pytest.raises(ValueError):
        parse_gtm_json("not json at all, no braces")
