"""
DigiCloset Backend API Service

Main FastAPI application for:
- Shopify OAuth & merchant management
- Billing & credit system
- Job queue management
- Orchestration between AI inference & database

Production-grade service with:
- Structured logging
- Request tracing
- Health checks
- Prometheus metrics
- Error handling
"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
    title="DigiCloset Backend API",
    description="Production Shopify SaaS backend service",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Metrics ============

request_count = Counter(
    'backend_api_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'backend_api_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ai_inference_duration = Histogram(
    'backend_ai_inference_duration_seconds',
    'AI inference call duration',
    ['operation']
)

# ============ Middleware ============

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Track request duration and count metrics"""
    request_id = request.headers.get("x-request-id") or str(time.time())
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Record metrics
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)
        
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": f"{process_time * 1000:.2f}"
            }
        )
        
        response.headers["X-Process-Time"] = str(process_time)
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
        "service": "backend-api",
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
    # Check database, Redis, AI inference service
    checks = {
        "database": "unknown",
        "redis": "unknown",
        "ai_inference": "unknown"
    }
    
    all_ready = all(v == "ready" for v in checks.values())
    
    return {
        "ready": all_ready,
        "checks": checks
    }


# ============ Include Routes ============

from .routes import tryon, billing, merchant

app.include_router(tryon.router, prefix="/api/v1", tags=["try-on"])
app.include_router(billing.router, prefix="/api/v1", tags=["billing"])
app.include_router(merchant.router, prefix="/api/v1", tags=["merchant"])


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
    }


# ============ Lifespan Events ============

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Backend API service starting up")
    # Initialize database connections, caches, etc.


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Backend API service shutting down")
    # Close database connections, etc.


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV") == "development"
    )
