from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.genai import types

from src.agents.gtm_agent.prompts import (
    GTM_AGENT_DESCRIPTION,
    build_gtm_instruction,
)
from src.configs.config import get_config
from src.schemas.gtm import GTMBrief


def _base_generate_config() -> types.GenerateContentConfig:
    cfg = get_config().gemini
    return types.GenerateContentConfig(
        temperature=cfg.temperature,
        max_output_tokens=cfg.max_output_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=cfg.thinking_budget),
    )


def create_doc_agent(market: str, industry: str) -> LlmAgent:
    """Pitch-deck mode: no tools; structured JSON output enforced via output_schema."""
    config = get_config()
    return LlmAgent(
        name="GTMDocAnalystAgent",
        model=config.gemini.model_name,
        description=GTM_AGENT_DESCRIPTION,
        instruction=build_gtm_instruction(market, industry),
        generate_content_config=_base_generate_config(),
        output_schema=GTMBrief,
    )


def create_url_agent(market: str, industry: str) -> LlmAgent:
    """URL mode: google_search grounding enabled. ADK/Gemini disallow
    output_schema together with tools, so we rely on the prompt-embedded JSON
    structure and parse the response.
    """
    config = get_config()
    return LlmAgent(
        name="GTMUrlAnalystAgent",
        model=config.gemini.model_name,
        description=GTM_AGENT_DESCRIPTION,
        instruction=build_gtm_instruction(market, industry),
        tools=[google_search],
        generate_content_config=_base_generate_config(),
    )
