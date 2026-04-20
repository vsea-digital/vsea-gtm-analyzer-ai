from fastapi import APIRouter

from src.configs.config import get_config
from src.models.models import CLAUDE_SONNET_4_6

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    config = get_config()
    return {
        "status": "ok",
        "service": config.project.name,
        "version": config.project.version,
        "model": CLAUDE_SONNET_4_6,
    }
