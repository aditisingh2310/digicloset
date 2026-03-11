"""
Inference Service Try-On Endpoint

FastAPI endpoint that handles try-on generation requests from the Shopify app.
"""

import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import httpx

from .tryon_service import get_tryon_service, TryOnService
from .replicate_client import ReplicateError

logger = logging.getLogger(__name__)


class TryOnGenerateRequest(BaseModel):
    """Request to generate try-on."""
    tryon_id: str
    shop_id: str
    user_image_url: str
    garment_image_url: str
    category: str = "upper_body"


class TryOnGenerateResponse(BaseModel):
    """Response from try-on generation."""
    tryon_id: str
    status: str
    message: str


# Create FastAPI app (if not already imported)
app = FastAPI(
    title="DigiCloset Inference Service",
    version="1.0.0",
    description="Virtual try-on generation service",
)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "inference-service"}


@app.post(
    "/api/v1/generate-tryon",
    response_model=TryOnGenerateResponse,
    summary="Generate virtual try-on",
)
async def generate_tryon(
    request: TryOnGenerateRequest,
    background_tasks: BackgroundTasks,
) -> TryOnGenerateResponse:
    """
    Generate virtual try-on image.

    This endpoint:
    1. Validates inputs
    2. Calls TryOnService for generation
    3. Saves result and notifies Shopify app
    4. Returns immediate response

    Args:
        request: Try-on generation request

    Returns:
        Status response
    """
    try:
        logger.info(
            f"Try-on request received: {request.tryon_id} "
            f"(shop: {request.shop_id}, category: {request.category})"
        )

        # Submit background task to generate try-on
        background_tasks.add_task(
            _process_tryon_generation,
            request.tryon_id,
            request.shop_id,
            request.user_image_url,
            request.garment_image_url,
            request.category,
        )

        return TryOnGenerateResponse(
            tryon_id=request.tryon_id,
            status="queued",
            message="Try-on generation started",
        )

    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to initiate try-on: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate generation")


@app.get(
    "/api/v1/status/{prediction_id}",
    summary="Get try-on generation status",
)
async def get_prediction_status(prediction_id: str) -> dict:
    """
    Get status of a Replicate prediction.

    Args:
        prediction_id: Replicate prediction ID

    Returns:
        Prediction status
    """
    try:
        from .replicate_client import get_replicate_client

        client = get_replicate_client()
        status = await client.get_prediction_status(prediction_id)
        return status

    except Exception as e:
        logger.error(f"Failed to get prediction status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# ============ Background Processing ============


async def _process_tryon_generation(
    tryon_id: str,
    shop_id: str,
    user_image_url: str,
    garment_image_url: str,
    category: str,
) -> None:
    """
    Background task to process try-on generation.

    This function:
    1. Generates try-on using TryOnService
    2. Saves result to storage
    3. Updates Shopify app with result
    4. Handles errors gracefully
    """
    tryon_service = get_tryon_service()
    start_time = datetime.now()

    try:
        logger.info(f"Processing try-on: {tryon_id}")

        # Generate try-on
        result = await tryon_service.generate_tryon(
            user_image_url=user_image_url,
            garment_image_url=garment_image_url,
            category=category,
        )

        if result.status == "error":
            logger.error(f"Try-on generation failed: {result.error}")
            await _notify_shopify_app(
                tryon_id=tryon_id,
                shop_id=shop_id,
                status="failed",
                error=result.error,
            )
            return

        # Save generated image
        try:
            from .storage_service import get_storage_service

            storage = get_storage_service()
            
            # Download generated image and save
            saved_url = await storage.download_and_save(
                result.image_url,
                filename=f"tryon_{tryon_id}.jpg",
            )

            logger.info(f"Saved try-on image: {saved_url}")

        except Exception as e:
            logger.warning(f"Failed to save image: {str(e)}")
            saved_url = result.image_url  # Fallback to Replicate URL

        # Notify Shopify app with result
        processing_time = (datetime.now() - start_time).total_seconds()
        await _notify_shopify_app(
            tryon_id=tryon_id,
            shop_id=shop_id,
            status="completed",
            image_url=saved_url,
            processing_time=processing_time,
            prediction_id=result.prediction_id,
        )

        logger.info(f"Try-on completed: {tryon_id} ({processing_time:.2f}s)")

    except Exception as e:
        logger.exception(f"Unexpected error in try-on processing: {str(e)}")
        await _notify_shopify_app(
            tryon_id=tryon_id,
            shop_id=shop_id,
            status="failed",
            error="Internal error during generation",
        )


async def _notify_shopify_app(
    tryon_id: str,
    shop_id: str,
    status: str,
    image_url: str = None,
    processing_time: float = None,
    prediction_id: str = None,
    error: str = None,
) -> None:
    """
    Notify Shopify app of try-on result.

    This would call a webhook or update a database that the Shopify app polls.
    """
    try:
        payload = {
            "tryon_id": tryon_id,
            "shop_id": shop_id,
            "status": status,
            "image_url": image_url,
            "processing_time": processing_time,
            "prediction_id": prediction_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        # Option 1: Call Shopify app webhook
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                "http://shopify-app:8000/api/v1/webhooks/inference",
                json=payload,
            )

        # Option 2: Update database (pseudo-code)
        # db.query(TryOnGeneration).filter(
        #     TryOnGeneration.id == tryon_id
        # ).update({
        #     "status": status,
        #     "generatedImageUrl": image_url,
        #     "processingTime": processing_time,
        #     "replicateId": prediction_id,
        #     "errorMessage": error,
        #     "completedAt": datetime.now() if status == "completed" else None,
        # })
        # db.commit()

        logger.info(f"Notified app of try-on result: {tryon_id}")

    except Exception as e:
        logger.error(f"Failed to notify app: {str(e)}")
        # Don't raise - this is best-effort notification
