from fastapi import APIRouter

from src.routes.analyze_doc.route import router as analyze_doc_router
from src.routes.analyze_url.route import router as analyze_url_router
from src.routes.health.route import router as health_router
from src.routes.upload.route import router as upload_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(upload_router)
api_router.include_router(analyze_doc_router)
api_router.include_router(analyze_url_router)
