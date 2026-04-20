import pytest
from pydantic import ValidationError

from src.schemas.gtm import GTMBrief


def test_valid_brief_parses(valid_brief):
    brief = GTMBrief.model_validate(valid_brief)
    assert brief.companyName == "Acme"
    assert brief.verdict == "Conditional Go"
    assert len(brief.scoreBreakdown) == 7
    assert len(brief.competitors) == 3
    assert len(brief.regulatory) == 3


def test_bad_verdict_rejected(valid_brief):
    valid_brief["verdict"] = "Maybe"
    with pytest.raises(ValidationError):
        GTMBrief.model_validate(valid_brief)


def test_score_range_enforced(valid_brief):
    valid_brief["gtmScore"] = 150
    with pytest.raises(ValidationError):
        GTMBrief.model_validate(valid_brief)
