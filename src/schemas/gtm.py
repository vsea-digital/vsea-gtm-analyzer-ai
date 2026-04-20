from typing import Literal

from pydantic import BaseModel, Field


Verdict = Literal["Strong Go", "Conditional Go", "Proceed with Caution", "No Go"]
# Frontend CSS keys off these exact strings (threat-High / reg-critical / …)
# so we pin them as enums rather than free-form strings.
Threat = Literal["High", "Medium", "Low"]
RegLevel = Literal["critical", "medium", "low"]


# Fields that are "flavor text" (notes, descriptions, weaknesses) default to ""
# because the model occasionally omits them even when the prompt demands the
# full structure. Structural fields (scores, list sizes) stay required — if
# those come back wrong, we want a 502, not silent garbage.


class ScoreBreakdownItem(BaseModel):
    dimension: str
    score: int
    max: int
    note: str = ""
    blocker: bool = False


class KeyStat(BaseModel):
    label: str = ""
    value: str = ""


class MarketOpportunity(BaseModel):
    headline: str = ""
    narrative: str = ""
    keyStats: list[KeyStat] = Field(default_factory=list)


class MarketSizingBand(BaseModel):
    label: str = ""
    value: str = ""
    pct: float = 0
    note: str = ""


class MarketSizing(BaseModel):
    tam: MarketSizingBand
    sam: MarketSizingBand
    som: MarketSizingBand
    cagr: str = ""
    growth: str = ""


class MarketAnalysis(BaseModel):
    overview: str = ""
    trends: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class Opportunity(BaseModel):
    title: str = ""
    desc: str = ""


class Competitor(BaseModel):
    rank: int
    name: str
    hq: str = ""
    desc: str = ""
    threat: Threat
    weakness: str = ""


class RegulatoryItem(BaseModel):
    level: RegLevel
    agency: str = ""
    title: str = ""
    desc: str = ""
    blocker: bool = False


class GtmPhase(BaseModel):
    timing: str = ""
    title: str = ""
    items: list[str] = Field(default_factory=list)


class GtmPlan(BaseModel):
    phase1: GtmPhase
    phase2: GtmPhase
    phase3: GtmPhase


class GTMBrief(BaseModel):
    companyName: str
    product: str
    gtmScore: int = Field(ge=0, le=100)
    structuralBlocker: bool = False
    blockerExplanation: str = ""
    verdict: Verdict
    verdictReason: str = ""
    summary: str = ""
    scoreBreakdown: list[ScoreBreakdownItem]
    marketOpportunity: MarketOpportunity
    marketSizing: MarketSizing
    marketAnalysis: MarketAnalysis
    opportunities: list[Opportunity]
    competitors: list[Competitor]
    regulatory: list[RegulatoryItem]
    gtmPlan: GtmPlan
