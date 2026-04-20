"""LLM model instances for the GTM analyzer agents.

Uses LiteLlm so we can talk to Anthropic's Claude Sonnet 4.6 through ADK's
non-Gemini model pathway. Reads ANTHROPIC_API_KEY from the environment.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from google.adk.models.lite_llm import LiteLlm, LiteLLMClient


CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"

# Anthropic's native server-side web search tool. litellm forwards this to
# the Anthropic API untouched and normalises the response back.
_WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}

# Anthropic marks responses from its server-executed tools with ids starting
# with "srvtoolu_". litellm surfaces those as ordinary tool_calls, which then
# confuses ADK into looking for a matching client-side tool. We scrub them so
# only the model's final text reaches ADK.
_SERVER_TOOL_ID_PREFIX = "srvtoolu_"


class _WebSearchLiteLLMClient(LiteLLMClient):
    """Injects Anthropic's web_search server tool and scrubs the server-
    tool-use call-ids that litellm surfaces back to the caller."""

    async def acompletion(self, model, messages, tools, **kwargs):
        augmented = [*(tools or []), _WEB_SEARCH_TOOL]
        result = await super().acompletion(
            model=model, messages=messages, tools=augmented, **kwargs
        )
        if kwargs.get("stream"):
            return _scrub_stream(result)
        _scrub_server_tool_calls(result)
        return result

    def completion(self, model, messages, tools, stream=False, **kwargs):
        augmented = [*(tools or []), _WEB_SEARCH_TOOL]
        return super().completion(
            model=model,
            messages=messages,
            tools=augmented,
            stream=stream,
            **kwargs,
        )


def _is_server_tool_call(tc: Any) -> bool:
    tc_id = getattr(tc, "id", "") or ""
    if tc_id.startswith(_SERVER_TOOL_ID_PREFIX):
        return True
    fn = getattr(tc, "function", None)
    return (getattr(fn, "name", "") or "") == _WEB_SEARCH_TOOL["name"]


def _scrub_server_tool_calls(response: Any) -> None:
    for choice in getattr(response, "choices", None) or []:
        msg = getattr(choice, "message", None)
        calls = getattr(msg, "tool_calls", None) if msg is not None else None
        if not calls:
            continue
        filtered = [c for c in calls if not _is_server_tool_call(c)]
        msg.tool_calls = filtered or None


async def _scrub_stream(stream: AsyncIterator[Any]) -> AsyncIterator[Any]:
    """Drop any tool_call chunks that belong to Anthropic's server-side
    web_search so ADK's streaming aggregator never sees them."""
    server_indices: set[int] = set()
    async for chunk in stream:
        for choice in getattr(chunk, "choices", None) or []:
            delta = getattr(choice, "delta", None)
            tcs = getattr(delta, "tool_calls", None) if delta is not None else None
            if not tcs:
                continue
            kept = []
            for tc in tcs:
                idx = getattr(tc, "index", None)
                if idx in server_indices:
                    continue
                if _is_server_tool_call(tc):
                    if idx is not None:
                        server_indices.add(idx)
                    continue
                kept.append(tc)
            delta.tool_calls = kept or None
        yield chunk


# litellm retries with exponential backoff on 429 / 5xx / timeouts /
# connection errors. 4xx client errors (bad key, grammar too large) are not
# retried.
_NUM_RETRIES = 3


def get_claude_sonnet_4_6() -> LiteLlm:
    return LiteLlm(
        model=f"anthropic/{CLAUDE_SONNET_4_6}",
        num_retries=_NUM_RETRIES,
    )


def get_claude_sonnet_4_6_with_web_search() -> LiteLlm:
    """Claude Sonnet 4.6 with Anthropic's native web_search server tool enabled."""
    return LiteLlm(
        model=f"anthropic/{CLAUDE_SONNET_4_6}",
        llm_client=_WebSearchLiteLLMClient(),
        num_retries=_NUM_RETRIES,
    )
