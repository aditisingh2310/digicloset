"""
Virtual Try-On API Routes

Endpoints for try-on generation, credit management, and status checking.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from packages.shared.models.tryon import (
    TryOnRequest,
    TryOnResponse,
    TryOnAsyncResponse,
    TryOnStatusResponse,
    ShopCreditsResponse,
    CreditCheckResponse,
    TryOnHistoryResponse,
    TryOnHistoryListResponse,
    TryOnStatus,
)
from packages.shared.exceptions import ValidationError, RateLimitError
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/try-on", tags=["try-on"])

# Import based on what's available in the backend
# These would come from your database models


async def get_current_shop(request) -> dict:
    """Get current shop from request context (from auth middleware)."""
    shop_id = getattr(request.state, "shop_id", None)
    if not shop_id:
        raise HTTPException(status_code=401, detail="Shop not authenticated")
    return {"shop_id": shop_id}


@router.post(
    "/generate",
    response_model=TryOnAsyncResponse,
    summary="Generate virtual try-on",
    description="Initiate a virtual try-on generation. Returns immediately with status.",
)
async def generate_tryon(
    request_data: TryOnRequest,
    request,
    db: Session = Depends(),  # Your DB dependency
) -> TryOnAsyncResponse:
    """
    Generate virtual try-on image.

    The endpoint will:
    1. Verify shop authentication
    2. Check credit balance
    3. Create generation record
    4. Call inference service asynchronously
    5. Return async status

    Returns:
        Async response with generation ID
    """
    shop = await get_current_shop(request)
    shop_id = shop["shop_id"]

    try:
        # Check if shop has credits
        credit_check = await _check_shop_credits(db, shop_id)
        if not credit_check["has_credits"]:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. {credit_check['message']}",
            )

        # Create try-on record in database
        tryon_record = await _create_tryon_record(
            db,
            shop_id=shop_id,
            user_image_url=str(request_data.user_image_url),
            garment_image_url=str(request_data.garment_image_url),
            product_id=request_data.product_id,
        )

        # Submit background job to generate try-on
        # This would call your queue worker or inference service
        await _submit_tryon_job(
            tryon_id=tryon_record.id,
            shop_id=shop_id,
            user_image_url=str(request_data.user_image_url),
            garment_image_url=str(request_data.garment_image_url),
            category=request_data.category,
        )

        logger.info(f"Try-on generation started: {tryon_record.id} for shop {shop_id}")

        return TryOnAsyncResponse(
            id=tryon_record.id,
            status=TryOnStatus.PENDING,
            created_at=tryon_record.createdAt,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to initiate try-on: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate try-on generation")


@router.get(
    "/{tryon_id}",
    response_model=TryOnStatusResponse,
    summary="Get try-on status",
    description="Check the status of a try-on generation.",
)
async def get_tryon_status(
    tryon_id: str,
    request,
    db: Session = Depends(),
) -> TryOnStatusResponse:
    """
    Get status of a try-on generation.

    Args:
        tryon_id: Try-on generation ID

    Returns:
        Status and details of the generation
    """
    try:
        shop = await get_current_shop(request)
        shop_id = shop["shop_id"]

        # Fetch from database (pseudo-code)
        # tryon = db.query(TryOnGeneration).filter(
        #     TryOnGeneration.id == tryon_id,
        #     TryOnGeneration.shopId == shop_id
        # ).first()

        # if not tryon:
        #     raise HTTPException(status_code=404, detail="Try-on not found")

        return TryOnStatusResponse(
            id=tryon_id,
            status=TryOnStatus.COMPLETED,
            generated_image_url="https://example.com/generated.jpg",
            processing_time=12.5,
            created_at=datetime.now(),
            completed_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get try-on status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get try-on status")


@router.get(
    "/credits/check",
    response_model=CreditCheckResponse,
    summary="Check available credits",
    description="Check if shop has available credits for try-on generation.",
)
async def check_credits(
    request,
    db: Session = Depends(),
) -> CreditCheckResponse:
    """Check if shop has available credits."""
    shop = await get_current_shop(request)
    shop_id = shop["shop_id"]

    try:
        result = await _check_shop_credits(db, shop_id)
        return CreditCheckResponse(
            has_credits=result["has_credits"],
            credits_remaining=result["credits_remaining"],
            message=result["message"],
        )

    except Exception as e:
        logger.exception(f"Failed to check credits: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check credits")


@router.get(
    "/credits/info",
    response_model=ShopCreditsResponse,
    summary="Get credit information",
    description="Get detailed credit usage information for the shop.",
)
async def get_credit_info(
    request,
    db: Session = Depends(),
) -> ShopCreditsResponse:
    """Get credit usage details."""
    shop = await get_current_shop(request)
    shop_id = shop["shop_id"]

    try:
        # Get credit info from database
        # credits = db.query(ShopCredits).filter(ShopCredits.shopId == shop_id).first()

        return ShopCreditsResponse(
            monthly_limit=100,
            credits_used=25,
            credits_remaining=75,
            reset_date=datetime.now() + timedelta(days=20),
        )

    except Exception as e:
        logger.exception(f"Failed to get credit info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get credit information")


@router.get(
    "/history",
    response_model=TryOnHistoryListResponse,
    summary="Get try-on history",
    description="Get paginated list of try-on generations for this shop.",
)
async def get_tryon_history(
    request,
    db: Session = Depends(),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> TryOnHistoryListResponse:
    """Get try-on generation history."""
    shop = await get_current_shop(request)
    shop_id = shop["shop_id"]

    try:
        # Query from database with pagination
        # total = db.query(TryOnGeneration).filter(
        #     TryOnGeneration.shopId == shop_id
        # ).count()
        #
        # tryons_db = db.query(TryOnGeneration).filter(
        #     TryOnGeneration.shopId == shop_id
        # ).order_by(desc(TryOnGeneration.createdAt)).offset(offset).limit(limit).all()

        tryons = [
            TryOnHistoryResponse(
                id="tryon_1",
                product_id="pid_123",
                generated_image_url="https://example.com/tryon1.jpg",
                status=TryOnStatus.COMPLETED,
                credits_used=1,
                processing_time=12.5,
                created_at=datetime.now(),
            )
        ]

        return TryOnHistoryListResponse(
            tryons=tryons,
            total=1,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.exception(f"Failed to get history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


# ============ Internal Helper Functions ============


async def _check_shop_credits(db: Session, shop_id: str) -> dict:
    """
    Check if shop has available credits.

    Returns:
        Dictionary with has_credits, credits_remaining, message
    """
    # This is pseudo-code - adapt to your actual DB models
    # credits = db.query(ShopCredits).filter(ShopCredits.shopId == shop_id).first()
    #
    # if not credits:
    #     # Initialize credits for new shop
    #     credits = ShopCredits(shopId=shop_id, monthlyLimit=100)
    #     db.add(credits)
    #     db.commit()

    # For demo purposes:
    credits_remaining = 75

    return {
        "has_credits": credits_remaining > 0,
        "credits_remaining": credits_remaining,
        "message": f"{credits_remaining} credits remaining this month"
        if credits_remaining > 0
        else "Monthly credit limit exceeded",
    }


async def _create_tryon_record(
    db: Session,
    shop_id: str,
    user_image_url: str,
    garment_image_url: str,
    product_id: str,
) -> object:
    """Create try-on record in database."""
    # This is pseudo-code
    # tryon = TryOnGeneration(
    #     shopId=shop_id,
    #     productId=product_id,
    #     userImageUrl=user_image_url,
    #     garmentImageUrl=garment_image_url,
    #     status="pending"
    # )
    # db.add(tryon)
    # db.commit()
    # db.refresh(tryon)

    class TryOnRecord:
        id = "tryon_123"
        createdAt = datetime.now()

    return TryOnRecord()


async def _submit_tryon_job(
    tryon_id: str,
    shop_id: str,
    user_image_url: str,
    garment_image_url: str,
    category: str = "upper_body",
) -> None:
    """Submit try-on job to Celery queue."""
    try:
        from services.queue_worker.tryon_tasks import generate_tryon_task

        # Submit task to Celery queue with automatic retry
        task = generate_tryon_task.delay(
            tryon_id=tryon_id,
            shop_id=shop_id,
            user_image_url=user_image_url,
            garment_image_url=garment_image_url,
            category=category,
        )

        logger.info(
            f"Submitted try-on job to queue: {tryon_id}",
            extra={
                "celery_task_id": task.id,
                "shop_id": shop_id,
            },
        )

    except ImportError:
        # Fallback: Call inference service directly if Celery not available
        logger.warning("Celery not available, falling back to direct HTTP request")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    "http://inference-service:8002/api/v1/generate-tryon",
                    json={
                        "tryon_id": tryon_id,
                        "shop_id": shop_id,
                        "user_image_url": user_image_url,
                        "garment_image_url": garment_image_url,
                        "category": category,
                    },
                    timeout=5,
                )
        except Exception as http_error:
            logger.error(f"HTTP fallback failed: {str(http_error)}")
            raise

    except Exception as e:
        logger.error(f"Failed to submit try-on job: {str(e)}")
        raise
