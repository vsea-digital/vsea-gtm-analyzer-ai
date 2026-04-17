from __future__ import annotations

import json
import re
import uuid

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.logging.custom_logger import Logging

LOGGER = Logging().get_logger("agent_runner")

APP_NAME = "vsea-gtm-analyzer-ai"


async def run_agent_once(
    agent: LlmAgent,
    parts: list[types.Part],
) -> str:
    """Run the agent with a single user message and return the concatenated text.

    Each call gets a fresh in-memory session — the analyzer is stateless.
    """
    session_service = InMemorySessionService()
    user_id = f"gtm-{uuid.uuid4()}"
    session = await session_service.create_session(app_name=APP_NAME, user_id=user_id)

    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    user_content = types.Content(role="user", parts=parts)

    collected: list[str] = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_content,
    ):
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            if part.text and not getattr(part, "thought", False):
                collected.append(part.text)

    text = "".join(collected).strip()
    if not text:
        raise RuntimeError("Agent produced no text output")
    return text


def parse_gtm_json(text: str) -> dict:
    """Port of parseGeminiResponse from the frontend HTML (lines 853-870).

    Strips markdown fences, tries strict JSON.parse, then falls back to
    extracting the first top-level { ... } block.
    """
    clean = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    clean = re.sub(r"```\s*", "", clean).strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", clean)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            first = clean.find("{")
            last = clean.rfind("}")
            if first != -1 and last != -1 and last > first:
                try:
                    return json.loads(clean[first : last + 1])
                except json.JSONDecodeError:
                    pass

    raise ValueError("Could not parse JSON from agent response")
