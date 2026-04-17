from fastapi import APIRouter

from src.configs.config import get_config

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    config = get_config()
    return {
        "status": "ok",
        "service": config.project.name,
        "version": config.project.version,
        "model": config.gemini.model_name,
    }
