from typing import Literal

from pydantic import BaseModel, Field


Verdict = Literal["Go", "Proceed with Caution", "Hold"]
Threat = Literal["High", "Medium", "Low"]
RegLevel = Literal["critical", "medium", "low"]


class ScoreBreakdownItem(BaseModel):
    dimension: str
    score: int
    max: int
    note: str


class KeyStat(BaseModel):
    label: str
    value: str


class MarketOpportunity(BaseModel):
    headline: str
    narrative: str
    keyStats: list[KeyStat]


class MarketSizingBand(BaseModel):
    label: str
    value: str
    pct: int
    note: str


class MarketSizing(BaseModel):
    tam: MarketSizingBand
    sam: MarketSizingBand
    som: MarketSizingBand
    cagr: str
    growth: str


class MarketAnalysis(BaseModel):
    overview: str
    trends: list[str]
    risks: list[str]


class Opportunity(BaseModel):
    title: str
    desc: str


class Competitor(BaseModel):
    rank: int
    name: str
    hq: str
    desc: str
    threat: Threat
    weakness: str


class RegulatoryItem(BaseModel):
    level: RegLevel
    agency: str
    title: str
    desc: str


class GtmPhase(BaseModel):
    timing: str
    title: str
    items: list[str]


class GtmPlan(BaseModel):
    phase1: GtmPhase
    phase2: GtmPhase
    phase3: GtmPhase


class GTMBrief(BaseModel):
    companyName: str
    product: str
    gtmScore: int = Field(ge=0, le=100)
    verdict: Verdict
    verdictReason: str
    summary: str
    scoreBreakdown: list[ScoreBreakdownItem]
    marketOpportunity: MarketOpportunity
    marketSizing: MarketSizing
    marketAnalysis: MarketAnalysis
    opportunities: list[Opportunity]
    competitors: list[Competitor]
    regulatory: list[RegulatoryItem]
    gtmPlan: GtmPlan
