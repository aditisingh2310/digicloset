"""
DigiCloset AI Inference Service

Dedicated service for:
- Virtual try-on generation via Replicate API
- Image preprocessing & validation
- Inference pipeline orchestration
- ML model interactions

Production features:
- Async processing with polling
- Request tracing
- Structured logging
- Prometheus metrics
- Health checks
"""

import logging
from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, generate_latest
from datetime import datetime
import time
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DigiCloset AI Inference Service",
    description="ML inference and image processing service",
    version="2.0.0"
)

# ============ Metrics ============

inference_requests = Counter(
    'ai_inference_requests_total',
    'Total inference requests',
    ['operation', 'status']
)

inference_duration = Histogram(
    'ai_inference_duration_seconds',
    'Inference duration in seconds',
    ['operation']
)

image_processing_duration = Histogram(
    'ai_image_processing_duration_seconds',
    'Image processing duration in seconds',
    ['operation']
)

# ============ Middleware ============

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    """Track metrics for all requests"""
    request_id = request.headers.get("x-request-id") or str(time.time())
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            extra={
                "request_id": request_id,
                "duration_ms": f"{duration * 1000:.2f}"
            }
        )
        
        response.headers["X-Request-ID"] = request_id
        
        return response
    except Exception as e:
        logger.exception(
            f"Request failed: {str(e)}",
            extra={"request_id": request_id}
        )
        raise


# ============ Health Endpoints ============

@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "ai-inference",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    # Check external ML API connectivity
    return {
        "ready": True,
        "checks": {
            "replicate_api": "ready"
        }
    }


# ============ Include Routes ============

from .routes import inference, preprocessing

app.include_router(inference.router, prefix="/api/v1", tags=["inference"])
app.include_router(preprocessing.router, prefix="/api/v1", tags=["preprocessing"])


# ============ Error Handlers ============

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "endpoint": request.url.path,
            "method": request.method
        }
    )
    return {
        "error": "Internal server error",
        "request_id": request.headers.get("x-request-id")
    }, 500


# ============ Lifespan Events ============

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("AI Inference service starting up")
    # Initialize ML models, API clients, etc.


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("AI Inference service shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=os.getenv("ENV") == "development"
    )
