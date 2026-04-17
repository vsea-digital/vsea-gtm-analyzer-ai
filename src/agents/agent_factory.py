from google.adk.agents import LlmAgent

from src.agents.gtm_agent.agent import create_doc_agent, create_url_agent


def create_document_agent(market: str, industry: str) -> LlmAgent:
    return create_doc_agent(market, industry)


def create_research_agent(market: str, industry: str) -> LlmAgent:
    return create_url_agent(market, industry)
