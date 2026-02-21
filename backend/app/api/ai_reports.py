from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.ai_reports import generate_catalog_report

router = APIRouter(prefix="/ai/reports", tags=["AI Reports"])


@router.post("/catalog")
def download_report(products: list):
    path = generate_catalog_report(products)
    return FileResponse(path)
