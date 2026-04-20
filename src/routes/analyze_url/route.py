from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from google.genai import types

from src.agents.agent_factory import create_research_agent
from src.agents.gtm_agent.prompts import build_url_user_message
from src.logging.custom_logger import Logging
from src.middlewares.auth import verify_service_key
from src.schemas.analyze import UrlAnalyzeRequest
from src.schemas.gtm import GTMBrief
from src.services.agent_runner import parse_gtm_json, run_agent_once

LOGGER = Logging().get_logger("analyze_url_route")

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/url", response_model=GTMBrief)
async def analyze_url(
    request: UrlAnalyzeRequest,
    _: str = Depends(verify_service_key),
) -> GTMBrief:
    url_str = str(request.url)
    user_msg = build_url_user_message(
        url_str,
        request.market,
        request.industry,
        company_description=request.company_description,
        customers=request.customers,
        stage=request.stage,
        business_model=request.business_model,
        gtm_goals=request.gtm_goals,
    )
    parts = [types.Part.from_text(text=user_msg)]

    agent = create_research_agent(request.market, request.industry)

    try:
        raw_text = await run_agent_once(agent, parts)
        payload = parse_gtm_json(raw_text)
        brief = GTMBrief.model_validate(payload)
    except Exception as e:  # noqa: BLE001
        LOGGER.error(f"URL analysis failed: {e}")
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")

    return brief
