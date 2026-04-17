from fastapi import HTTPException, Request


def verify_service_key(request: Request) -> str:
    from src.configs.config import get_config

    config = get_config()
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != config.secrets.SERVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
