"""
Try-On Generation Routes - Async Queue Integration

Production endpoints for:
- Async job submission with Redis queue
- Job status polling
- Result caching
- Billing limits checking
- Usage tracking
"""

import logging
import os
from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ MODELS ============

class TryOnRequest(BaseModel):
    """Try-on generation request"""
    user_image_url: HttpUrl
    garment_image_url: HttpUrl
    product_id: str
    category: str = "upper_body"
    shop_id: int


class TryOnJobResponse(BaseModel):
    """Response when job is submitted"""
    job_id: str
    status: str
    message: str


class TryOnStatusResponse(BaseModel):
    """Status of a pending/completed job"""
    job_id: str
    status: str  # pending, processing, completed, failed
    image_url: Optional[str] = None
    generation_time: Optional[int] = None  # milliseconds
    error: Optional[str] = None
    created_at: datetime


# ============ ENDPOINTS ============

@router.post("/try-on/request", response_model=TryOnJobResponse)
async def submit_tryon_request(
    request: TryOnRequest,
    x_shop_id: Optional[int] = Header(None)
):
    """
    Submit async try-on generation request.
    
    Returns immediately with job_id for polling.
    
    Pipeline:
    1. Validate billing limits
    2. Submit Celery task
    3. Create database record
    4. Return job_id
    
    Query params:
    - user_image_url: URL to user's image
    - garment_image_url: URL to garment image
    - product_id: Product ID
    - category: Clothing category (default: upper_body)
    - shop_id: Shopify store ID (from header or body)
    """
    try:
        from services.backend_api.app.services.billing_service import BillingService
        from sqlalchemy import create_engine, text
        
        # Use header shop_id or request body shop_id
        shop_id = x_shop_id or request.shop_id or None
        if not shop_id:
            raise HTTPException(status_code=400, detail="shop_id required")
        
        logger.info(f"Try-on request from shop={shop_id}, product={request.product_id}")
        
        # ===== CHECK BILLING LIMITS =====
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL not configured")
            raise HTTPException(status_code=500, detail="Configuration error")
        
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            # Get billing status
            result = conn.execute(text("""
                SELECT generation_limit, used_generations FROM store_plans
                WHERE shop_id = :shop_id
            """), {"shop_id": shop_id}).first()
            
            if result:
                limit, used = result
                if used >= limit:
                    logger.warning(f"Billing limit reached for shop={shop_id}")
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Generation limit reached",
                            "limit": limit,
                            "used": used,
                            "remaining": 0
                        }
                    )
                remaining = limit - used
            else:
                # New shop, default to free plan
                logger.info(f"Creating default plan for shop={shop_id}")
                remaining = 50  # Free tier
        
        # ===== CREATE JOB =====
        job_id = str(uuid.uuid4())
        
        with engine.connect() as conn:
            # Insert job record
            conn.execute(text("""
                INSERT INTO tryon_job (
                    id, shop_id, celery_task_id, status,
                    user_image_url, garment_image_url, product_id, category,
                    created_at, updated_at
                ) VALUES (
                    :id, :shop_id, :task_id, 'pending',
                    :user_url, :garment_url, :product_id, :category,
                    NOW(), NOW()
                )
            """), {
                "id": job_id,
                "shop_id": shop_id,
                "task_id": job_id,
                "user_url": str(request.user_image_url),
                "garment_url": str(request.garment_image_url),
                "product_id": request.product_id,
                "category": request.category
            })
            conn.commit()
        
        # ===== SUBMIT TO CELERY QUEUE =====
        from queue_worker.tryon_tasks import generate_tryon_task
        
        celery_task = generate_tryon_task.delay(
            job_id=job_id,
            shop_id=shop_id,
            product_id=request.product_id,
            user_image_url=str(request.user_image_url),
            garment_image_url=str(request.garment_image_url),
            category=request.category
        )
        
        logger.info(f"Submitted job {job_id} to queue (celery={celery_task.id})")
        
        return TryOnJobResponse(
            job_id=job_id,
            status="pending",
            message=f"Try-on generation queued. {remaining} generations remaining this month."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to submit try-on request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit request")


@router.get("/try-on/status/{job_id}", response_model=TryOnStatusResponse)
async def get_tryon_status(job_id: str):
    """
    Get status of a try-on generation job.
    
    Returns:
    - pending: Job is in queue or processing
    - processing: Active processing
    - completed: Ready at image_url
    - failed: See error message
    """
    try:
        from sqlalchemy import create_engine, text
        
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, status, result_image_url, error_message, created_at
                FROM tryon_job WHERE id = :job_id
            """), {"job_id": job_id}).first()
            
            if not result:
                raise HTTPException(status_code=404, detail="Job not found")
            
            job_id_db, status, image_url, error, created = result
            
            # Calculate generation time if completed
            gen_time = None
            if status == "completed" and image_url:
                from datetime import datetime as dt
                if hasattr(created, 'timestamp'):
                    gen_time = int((dt.utcnow() - created).total_seconds() * 1000)
            
            return TryOnStatusResponse(
                job_id=job_id,
                status=status,
                image_url=image_url,
                generation_time=gen_time,
                error=error,
                created_at=created
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get job status {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve status")


@router.get("/try-on/history", response_model=dict)
async def get_tryon_history(
    shop_id: int,
    limit: int = 20,
    offset: int = 0
):
    """
    Get try-on generation history for a shop.
    
    Query params:
    - shop_id: Shopify store ID
    - limit: Results per page (max 100)
    - offset: Pagination offset
    """
    try:
        from sqlalchemy import create_engine, text
        
        if limit > 100:
            limit = 100
        
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            # Get total count
            count = conn.execute(text("""
                SELECT COUNT(*) FROM tryon_job WHERE shop_id = :shop_id
            """), {"shop_id": shop_id}).scalar()
            
            # Get page
            results = conn.execute(text("""
                SELECT id, status, product_id, result_image_url, created_at, updated_at
                FROM tryon_job
                WHERE shop_id = :shop_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """), {
                "shop_id": shop_id,
                "limit": limit,
                "offset": offset
            }).fetchall()
            
            jobs = [
                {
                    "job_id": r[0],
                    "status": r[1],
                    "product_id": r[2],
                    "image_url": r[3],
                    "created_at": r[4],
                    "updated_at": r[5]
                }
                for r in results
            ]
            
            return {
                "jobs": jobs,
                "total": count,
                "limit": limit,
                "offset": offset
            }
        
    except Exception as e:
        logger.exception(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


# ===== (Legacy endpoints kept for compatibility) =====

@router.post("/try-on/generate", response_model=dict)
async def generate_tryon(request: TryOnRequest):
    """
    Legacy endpoint - use /try-on/request instead.
    
    Redirects to async queue system.
    """
    logger.warning("Deprecated endpoint /try-on/generate used")
    
    # Forward to new endpoint
    response = await submit_tryon_request(request)
    return {
        "job_id": response.job_id,
        "status": response.status,
        "created_at": datetime.utcnow().isoformat()
    }


@router.get("/try-on/{tryon_id}")
async def get_tryon(tryon_id: str):
    """Legacy endpoint - use /try-on/status/{job_id} instead"""
    logger.warning(f"Deprecated endpoint /try-on/{tryon_id} used")
    
    return await get_tryon_status(tryon_id)
            response = await client.post(
                f"{os.getenv('AI_INFERENCE_URL')}/generate-tryon",
                json={
                    "user_image_url": str(request.user_image_url),
                    "garment_image_url": str(request.garment_image_url),
                    "product_id": request.product_id,
                    "category": request.category
                },
                timeout=30
            )
        
        if response.status_code != 200:
            logger.error(f"AI service error: {response.text}")
            raise HTTPException(status_code=502, detail="AI service error")
        
        result = response.json()
        
        return {
            "id": result.get("prediction_id"),
            "status": "processing",
            "created_at": datetime.now().isoformat()
        }
    
    except httpx.TimeoutException:
        logger.error("AI service timeout")
        raise HTTPException(status_code=504, detail="AI service timeout")
    except Exception as e:
        logger.exception(f"Failed to generate try-on: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/try-on/{tryon_id}", response_model=TryOnResponse)
async def get_tryon_status(tryon_id: str):
    """Get try-on generation status"""
    try:
        # Query database or AI inference service
        logger.info(f"Checking status for: {tryon_id}")
        
        # Placeholder
        return TryOnResponse(
            id=tryon_id,
            status="processing",
            created_at=datetime.now(),
            processing_time=None
        )
    except Exception as e:
        logger.exception(f"Failed to get status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/try-on/history", response_model=dict)
async def get_tryon_history(limit: int = 10, offset: int = 0):
    """Get try-on generation history"""
    try:
        logger.info(f"Fetching history: limit={limit}, offset={offset}")
        
        return {
            "tryons": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.exception(f"Failed to fetch history: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error")


import os
