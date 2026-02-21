from fastapi import APIRouter

# Import feature routers
from app.api.ai_products import router as ai_products_router

api_router = APIRouter()

# Register routers
api_router.include_router(ai_products_router)
from app.api.ai_bulk import router as ai_bulk_router
from app.api.ai_usage import router as ai_usage_router
api_router.include_router(ai_bulk_router)
api_router.include_router(ai_usage_router)
from app.api.ai_reports import router as ai_reports_router
from app.api.ai_chat import router as ai_chat_router
