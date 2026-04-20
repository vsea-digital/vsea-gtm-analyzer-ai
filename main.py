import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.configs.config import get_config
from src.logging.custom_logger import Logging
from src.models.models import CLAUDE_SONNET_4_6
from src.routes import api_router

LOGGER = Logging().get_logger("main")


def _parse_origins(raw: str) -> list[str]:
    if not raw or raw.strip() == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    config = get_config()

    app = FastAPI(
        title=f"{config.project.name} API",
        description=(
            "ADK-powered GTM analyzer agents for VentureSea, driven by "
            "Claude Sonnet 4.6 via LiteLlm. Two endpoints: /analyze/document "
            "(pitch deck) and /analyze/url (website with Anthropic's native "
            "web_search grounding)."
        ),
        version=config.project.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    origins = _parse_origins(config.secrets.CORS_ORIGINS)
    origin_regex = config.secrets.CORS_ORIGIN_REGEX or None
    cors_kwargs: dict = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    # Starlette forbids "*" origins together with allow_credentials=True.
    # When the app is wide-open, drop credentials so preflight still works.
    if origins == ["*"] and not origin_regex:
        cors_kwargs["allow_origins"] = ["*"]
        cors_kwargs["allow_credentials"] = False
    else:
        cors_kwargs["allow_origins"] = [] if origins == ["*"] else origins
        if origin_regex:
            cors_kwargs["allow_origin_regex"] = origin_regex

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    app.include_router(api_router)

    @app.on_event("startup")
    async def startup():
        LOGGER.info(
            f"Starting {config.project.name} v{config.project.version} "
            f"(model={CLAUDE_SONNET_4_6})"
        )
        if not os.getenv("ANTHROPIC_API_KEY"):
            LOGGER.warning(
                "ANTHROPIC_API_KEY is not set — /analyze endpoints will fail"
            )
        if not config.secrets.SERVICE_API_KEY:
            LOGGER.warning(
                "SERVICE_API_KEY is not set — /analyze endpoints will reject all requests"
            )
        if not config.secrets.GCS_BUCKET_NAME:
            LOGGER.warning("GCS_BUCKET_NAME is not set — /upload will fail")

    @app.get("/")
    async def root():
        return {
            "service": config.project.name,
            "version": config.project.version,
            "status": "operational",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run("main:app", host=config.api.host, port=config.api.port, reload=True)
