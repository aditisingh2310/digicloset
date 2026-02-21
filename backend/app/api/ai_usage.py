from fastapi import APIRouter
from app.models.ai_usage import AIUsage

router = APIRouter(prefix="/ai/usage", tags=["AI Usage"])

usage_store = AIUsage()


@router.get("/")
def get_usage():
    return {
        "scans": usage_store.scans,
        "credits_used": usage_store.credits_used,
        "history": usage_store.history
    }
