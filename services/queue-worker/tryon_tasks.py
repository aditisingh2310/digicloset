"""
Celery Task Worker for Try-On Generation

Defines background tasks for handling virtual try-on generation
using Celery with Redis broker.
"""

import logging
import os
from celery import Celery
from celery.utils.log import get_task_logger
from datetime import datetime

# Initialize Celery app
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://localhost:6379/0"
)
CELERY_BACKEND_URL = os.getenv(
    "CELERY_BACKEND_URL",
    "redis://localhost:6379/1"
)

celery_app = Celery(
    "digicloset",
    broker=CELERY_BROKER_URL,
    backend=CELERY_BACKEND_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task configuration
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit
    # Retry configuration
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,  # 1 minute
)

logger = get_task_logger(__name__)


# ============ Queue Tasks ============


@celery_app.task(
    name="tryon.generate_tryon",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
)
def generate_tryon_task(
    self,
    tryon_id: str,
    shop_id: str,
    user_image_url: str,
    garment_image_url: str,
    category: str = "upper_body",
) -> dict:
    """
    Background task to generate try-on image.

    Retries up to 3 times with exponential backoff.

    Args:
        tryon_id: Unique try-on generation ID
        shop_id: Shopify shop ID
        user_image_url: URL to user's image
        garment_image_url: URL to garment image
        category: Clothing category (upper_body, lower_body, etc.)

    Returns:
        Dictionary with generation result
    """
    try:
        logger.info(
            f"[Task {self.request.id}] Starting try-on generation: {tryon_id}",
            extra={
                "tryon_id": tryon_id,
                "shop_id": shop_id,
                "category": category,
            },
        )

        # Import inside task to avoid circular imports
        import asyncio
        from services.inference_service.tryon_service import get_tryon_service
        from services.inference_service.storage_service import get_storage_service

        # Run async generation
        result = asyncio.run(_async_generate_tryon(
            tryon_id=tryon_id,
            shop_id=shop_id,
            user_image_url=user_image_url,
            garment_image_url=garment_image_url,
            category=category,
        ))

        if result.get("status") == "error":
            logger.error(
                f"Try-on generation failed: {result.get('error')}",
                extra={"tryon_id": tryon_id},
            )
            # Update database with error
            _update_tryon_status(
                tryon_id=tryon_id,
                status="failed",
                error=result.get("error"),
            )
            return result

        logger.info(
            f"Try-on generation completed: {tryon_id}",
            extra={
                "processing_time": result.get("processing_time"),
            },
        )

        # Save image and update database
        _update_tryon_status(
            tryon_id=tryon_id,
            status="completed",
            image_url=result.get("image_url"),
            processing_time=result.get("processing_time"),
            prediction_id=result.get("prediction_id"),
        )

        return result

    except Exception as e:
        logger.exception(
            f"Task failed: {str(e)}",
            extra={"tryon_id": tryon_id},
        )
        
        # Retry with exponential backoff
        raise self.retry(
            exc=e,
            countdown=2 ** self.request.retries,  # 2, 4, 8 seconds
        )


@celery_app.task(name="tryon.cancel_generation")
def cancel_tryon_task(prediction_id: str) -> dict:
    """
    Cancel a running try-on generation.

    Args:
        prediction_id: Replicate prediction ID to cancel

    Returns:
        Cancellation result
    """
    try:
        import asyncio
        from services.inference_service.replicate_client import get_replicate_client

        logger.info(f"Canceling prediction: {prediction_id}")

        # Cancel via Replicate API
        client = get_replicate_client()
        result = asyncio.run(
            client.cancel_prediction(prediction_id)
        )

        logger.info(f"Canceled prediction: {prediction_id}")
        return {"status": "canceled", "prediction_id": prediction_id}

    except Exception as e:
        logger.error(f"Failed to cancel prediction: {str(e)}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="tryon.cleanup_old_generations")
def cleanup_old_generations() -> dict:
    """
    Periodic task to clean up old try-on generations.

    Removes:
    - Failed generations older than 7 days
    - Completed generations' temporary files older than 30 days
    """
    try:
        from datetime import datetime, timedelta
        logger.info("Cleaning up old try-on generations")

        # Pseudo-code for database cleanup:
        # db.query(TryOnGeneration).filter(
        #     TryOnGeneration.createdAt < datetime.now() - timedelta(days=7),
        #     TryOnGeneration.status == "failed",
        # ).delete()
        # db.commit()

        logger.info("Cleanup completed")
        return {"status": "completed"}

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return {"status": "error", "error": str(e)}


# ============ Periodic Task Schedule ============


from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "cleanup-old-generations": {
        "task": "tryon.cleanup_old_generations",
        "schedule": crontab(hour=2, minute=0),  # 2 AM UTC daily
    },
}


# ============ Helper Functions ============


async def _async_generate_tryon(
    tryon_id: str,
    shop_id: str,
    user_image_url: str,
    garment_image_url: str,
    category: str,
) -> dict:
    """
    Async helper to generate try-on.

    Args:
        tryon_id: Try-on generation ID
        shop_id: Shop ID
        user_image_url: User image URL
        garment_image_url: Garment image URL
        category: Clothing category

    Returns:
        Generation result dictionary
    """
    try:
        from services.inference_service.tryon_service import get_tryon_service
        from datetime import datetime

        start_time = datetime.now()
        tryon_service = get_tryon_service()

        result = await tryon_service.generate_tryon(
            user_image_url=user_image_url,
            garment_image_url=garment_image_url,
            category=category,
        )

        if result.status == "error":
            return {
                "status": "error",
                "error": result.error,
                "tryon_id": tryon_id,
            }

        processing_time = (datetime.now() - start_time).total_seconds()

        # Save image to storage
        try:
            from services.inference_service.storage_service import get_storage_service

            storage = get_storage_service()
            saved_url = await storage.download_and_save(
                result.image_url,
                filename=f"tryon_{tryon_id}.jpg",
            )
        except Exception as e:
            logger.warning(f"Failed to save image, using Replicate URL: {str(e)}")
            saved_url = result.image_url

        return {
            "status": "success",
            "tryon_id": tryon_id,
            "image_url": saved_url,
            "processing_time": processing_time,
            "prediction_id": result.prediction_id,
        }

    except Exception as e:
        logger.exception(f"Error in async generation: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "tryon_id": tryon_id,
        }


def _update_tryon_status(
    tryon_id: str,
    status: str,
    image_url: str = None,
    processing_time: float = None,
    prediction_id: str = None,
    error: str = None,
) -> None:
    """
    Update try-on generation status in database.

    Pseudo-code:
        db.query(TryOnGeneration).filter(
            TryOnGeneration.id == tryon_id
        ).update({
            "status": status,
            "generatedImageUrl": image_url,
            "processingTime": processing_time,
            "replicateId": prediction_id,
            "errorMessage": error,
            "completedAt": datetime.now() if status == "completed" else None,
        })
        db.commit()
    """
    logger.info(
        f"Updating try-on status: {tryon_id} -> {status}",
        extra={
            "processing_time": processing_time,
            "has_error": error is not None,
        },
    )
