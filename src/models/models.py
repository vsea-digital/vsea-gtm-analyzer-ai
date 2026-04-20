"""LLM model instances for the GTM analyzer agents.

Uses LiteLlm so we can talk to Anthropic's Claude Sonnet 4.6 through ADK's
non-Gemini model pathway. Reads ANTHROPIC_API_KEY from the environment.
"""

from __future__ import annotations

from google.adk.models.lite_llm import LiteLlm


CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"


def get_claude_sonnet_4_6() -> LiteLlm:
    return LiteLlm(model=f"anthropic/{CLAUDE_SONNET_4_6}")
