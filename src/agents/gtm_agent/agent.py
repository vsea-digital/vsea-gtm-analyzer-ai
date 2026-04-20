from __future__ import annotations

from google.adk.agents import LlmAgent
from google.genai import types

from src.agents.gtm_agent.prompts import (
    GTM_AGENT_DESCRIPTION,
    build_gtm_instruction,
)
from src.configs.config import get_config
from src.models import (
    get_claude_sonnet_4_6,
    get_claude_sonnet_4_6_with_web_search,
)


def _base_generate_config() -> types.GenerateContentConfig:
    cfg = get_config().gemini
    return types.GenerateContentConfig(
        temperature=cfg.temperature,
        max_output_tokens=cfg.max_output_tokens,
    )


def create_doc_agent(market: str, industry: str) -> LlmAgent:
    """Pitch-deck mode: no tools. We used to pin Gemini output via
    output_schema=GTMBrief, but Anthropic rejects the compiled strict grammar
    for a schema this size, so we rely on the prompt's JSON contract and let
    the route do parse_gtm_json + GTMBrief.model_validate instead."""
    return LlmAgent(
        name="GTMDocAnalystAgent",
        model=get_claude_sonnet_4_6(),
        description=GTM_AGENT_DESCRIPTION,
        instruction=build_gtm_instruction(market, industry),
        generate_content_config=_base_generate_config(),
    )


def create_url_agent(market: str, industry: str) -> LlmAgent:
    """URL mode: Anthropic's native web_search server tool is enabled at the
    LiteLlm client layer so Claude can browse the target company website.
    We skip output_schema so the tool-call/response flow stays clean, and
    rely on the prompt-embedded JSON structure + parse_gtm_json downstream.
    """
    return LlmAgent(
        name="GTMUrlAnalystAgent",
        model=get_claude_sonnet_4_6_with_web_search(),
        description=GTM_AGENT_DESCRIPTION,
        instruction=build_gtm_instruction(market, industry),
        generate_content_config=_base_generate_config(),
    )
