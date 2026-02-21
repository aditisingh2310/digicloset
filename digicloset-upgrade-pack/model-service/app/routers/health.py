"""
Health and readiness probes for the model-service.
Exposes /health (liveness) and /ready (readiness) endpoints for Kubernetes and Docker orchestration.
"""

import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

_start_time = time.time()


@router.get("/health")
async def health_check():
    """
    Liveness probe. Returns service status, uptime, and loaded components.
    Always returns 200 if the process is running.
    """
    from app.services.cache import embedding_cache, color_cache

    uptime_seconds = round(time.time() - _start_time, 1)

    return JSONResponse(content={
        "status": "healthy",
        "uptime_seconds": uptime_seconds,
        "cache": {
            "embeddings": embedding_cache.stats,
            "colors": color_cache.stats,
        },
    })


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe. Returns 200 only when all critical ML services are initialized.
    Returns 503 if any required service is still loading.
    """
    # Import serve module to check global service state
    try:
        from serve import embedding_service, vector_store, color_extractor, ranking_service

        services = {
            "embedding_service": embedding_service is not None,
            "vector_store": vector_store is not None,
            "color_extractor": color_extractor is not None,
            "ranking_service": ranking_service is not None,
        }

        all_ready = all(services.values())

        if not all_ready:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "services": services}
            )

        return JSONResponse(content={"status": "ready", "services": services})

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )
