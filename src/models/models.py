"""LLM model instances for the GTM analyzer agents.

Uses LiteLlm so we can talk to Anthropic's Claude Sonnet 4.6 through ADK's
non-Gemini model pathway.
"""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm


CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"


def get_claude_sonnet_4_6() -> LiteLlm:
    """Return a LiteLlm wrapper for Claude Sonnet 4.6.

    Routing:
    - If ANTHROPIC_API_BASE is set (e.g. VentureSea's Claude proxy), route
      the call through that endpoint using LiteLlm's OpenAI-compatible path.
    - Otherwise, call Anthropic directly via ANTHROPIC_API_KEY.
    """
    api_base = os.getenv("ANTHROPIC_API_BASE", "").strip()

    if api_base:
        return LiteLlm(
            model=f"openai/{CLAUDE_SONNET_4_6}",
            api_base=api_base,
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        )

    return LiteLlm(model=f"anthropic/{CLAUDE_SONNET_4_6}")
