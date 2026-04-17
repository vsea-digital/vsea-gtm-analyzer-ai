from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from google.genai import types

from src.agents.agent_factory import create_document_agent
from src.agents.gtm_agent.prompts import build_doc_user_message
from src.logging.custom_logger import Logging
from src.middlewares.auth import verify_service_key
from src.schemas.analyze import DocumentAnalyzeRequest
from src.schemas.gtm import GTMBrief
from src.services.agent_runner import parse_gtm_json, run_agent_once
from src.services.gcs.client import delete_object, download_bytes, parse_gcs_uri
from src.services.ingestion.pdf_loader import pdf_to_parts
from src.services.ingestion.pptx_loader import pptx_to_parts

LOGGER = Logging().get_logger("analyze_doc_route")

router = APIRouter(prefix="/analyze", tags=["analyze"])


def _is_pdf(blob_name: str) -> bool:
    return blob_name.lower().endswith(".pdf")


def _is_pptx(blob_name: str) -> bool:
    return blob_name.lower().endswith(".pptx")


@router.post("/document", response_model=GTMBrief)
async def analyze_document(
    request: DocumentAnalyzeRequest,
    _: str = Depends(verify_service_key),
) -> GTMBrief:
    try:
        _, blob_name = parse_gcs_uri(request.gcs_uri)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        data = download_bytes(request.gcs_uri)
    except Exception as e:  # noqa: BLE001
        LOGGER.error(f"GCS download failed: {e}")
        raise HTTPException(status_code=502, detail=f"Download from GCS failed: {e}")

    if _is_pdf(blob_name):
        doc_parts = pdf_to_parts(data)
        is_pdf = True
    elif _is_pptx(blob_name):
        doc_parts = pptx_to_parts(data)
        is_pdf = False
    else:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported document type. Only .pdf and .pptx are supported. "
                "Legacy .ppt files must be re-saved as .pptx."
            ),
        )

    user_msg = build_doc_user_message(request.market, request.industry, is_pdf=is_pdf)
    parts: list[types.Part] = [*doc_parts, types.Part.from_text(text=user_msg)]

    agent = create_document_agent(request.market, request.industry)

    try:
        raw_text = await run_agent_once(agent, parts)
        payload = parse_gtm_json(raw_text)
        brief = GTMBrief.model_validate(payload)
    except Exception as e:  # noqa: BLE001
        LOGGER.error(f"Agent run failed: {e}")
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")
    finally:
        delete_object(request.gcs_uri)

    return brief
