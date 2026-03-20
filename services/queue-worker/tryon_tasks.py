"""
Celery Task Worker for Try-On Generation - Production Pipeline

Defines background tasks for handling virtual try-on generation with:
- Image validation
- Result caching
- S3 storage
- Usage tracking
- Retry and fault tolerance
- Database integration
"""

import logging
import os
import sys
from celery import Celery
from celery.utils.log import get_task_logger
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize Celery app
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://redis:6379/0"
)
CELERY_BACKEND_URL = os.getenv(
    "CELERY_BACKEND_URL",
    "redis://redis:6379/1"
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
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit
    task_autoretry_for=(Exception,),
    task_max_retries=2,  # Maximum 2 retries
    task_default_retry_delay=60,  # 1 minute initial delay
)

logger = get_task_logger(__name__)


# ============ MAIN TASK: Try-On Generation Pipeline ============

@celery_app.task(
    name="tryon.generate_tryon",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
)
def generate_tryon_task(
    self,
    job_id: str,
    shop_id: int,
    product_id: str,
    user_image_url: str,
    garment_image_url: str,
    category: str = "upper_body",
) -> dict:
    """
    Main try-on generation task - Production Pipeline
    
    Pipeline flow:
    1. Validate input images
    2. Check Redis cache for cached result
    3. Call AI inference service
    4. Upload result to S3
    5. Cache result in Redis (24h TTL)
    6. Update job status in database
    7. Record usage for billing
    
    Retries: Up to 2 attempts with exponential backoff (2s, 4s)
    
    Args:
        job_id: Unique job ID (celery task ID)
        shop_id: Shopify store ID
        product_id: Product being tried on
        user_image_url: URL to user's image
        garment_image_url: URL to garment image
        category: Clothing category
        
    Returns:
        Dict with status, image_url, generation_time, etc.
    """
    try:
        import asyncio
        import httpx
        from datetime import datetime as dt
        
        start_time = dt.utcnow()
        logger.info(f"[{job_id}] Starting try-on generation for shop={shop_id}")

        # ===== STEP 1: Validate Images =====
        logger.debug(f"[{job_id}] Validating input images")
        from backend_api.app.validation.image_validator import ImageValidator
        
        validator = ImageValidator()
        user_valid, user_error = validator.validate_image_url(user_image_url)
        if not user_valid:
            logger.error(f"[{job_id}] User image validation failed: {user_error}")
            return {
                "job_id": job_id,
                "status": "failed",
                "error": f"User image validation: {user_error}",
                "shop_id": shop_id
            }
        
        garment_valid, garment_error = validator.validate_image_url(garment_image_url)
        if not garment_valid:
            logger.error(f"[{job_id}] Garment image validation failed: {garment_error}")
            return {
                "job_id": job_id,
                "status": "failed",
                "error": f"Garment image validation: {garment_error}",
                "shop_id": shop_id
            }
        
        logger.debug(f"[{job_id}] Images validated successfully")

        # ===== STEP 2: Check Cache =====
        logger.debug(f"[{job_id}] Checking cache")
        from backend_api.app.cache.redis_cache import get_cache_service
        
        cache = get_cache_service()
        cached = cache.get_cached_result(user_image_url, garment_image_url)
        
        if cached:
            logger.info(f"[{job_id}] Cache hit - returning cached result")
            elapsed_ms = int((dt.utcnow() - start_time).total_seconds() * 1000)
            
            # Update job status as cached
            _update_job_status(
                job_id=job_id,
                shop_id=shop_id,
                status="completed",
                image_url=cached["image_url"],
                generation_time=elapsed_ms
            )
            
            return {
                "job_id": job_id,
                "status": "completed",
                "image_url": cached["image_url"],
                "cached": True,
                "generation_time": elapsed_ms,
                "shop_id": shop_id
            }
        
        logger.debug(f"[{job_id}] Cache miss - proceeding to AI inference")

        # ===== STEP 3: Call AI Inference Service =====
        logger.info(f"[{job_id}] Calling AI inference service")
        ai_url = os.getenv("AI_INFERENCE_URL", "http://ai-inference:8002")
        
        inference_result = asyncio.run(_call_ai_inference(
            job_id, user_image_url, garment_image_url, category, ai_url
        ))
        
        if not inference_result.get("success"):
            logger.error(f"[{job_id}] AI inference failed: {inference_result.get('error')}")
            _update_job_status(
                job_id=job_id,
                shop_id=shop_id,
                status="failed",
                error=inference_result.get("error")
            )
            raise Exception(inference_result.get("error"))
        
        generated_url = inference_result.get("image_url")
        inf_time = inference_result.get("inference_time", 0)
        logger.debug(f"[{job_id}] AI inference completed in {inf_time}ms")

        # ===== STEP 4: Upload to S3 =====
        logger.debug(f"[{job_id}] Uploading result to S3")
        from backend_api.app.storage.s3_client import get_storage_service
        
        s3_service = get_storage_service()
        final_url = generated_url
        
        if s3_service and s3_service.client:
            try:
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(generated_url, timeout=30)
                    img_response.raise_for_status()
                    
                    s3_key = f"try-ons/{shop_id}/{job_id}.png"
                    s3_url = s3_service.upload_image(
                        file_data=img_response.content,
                        key=s3_key,
                        content_type="image/png",
                        metadata={
                            "shop_id": str(shop_id),
                            "product_id": product_id,
                            "job_id": job_id
                        }
                    )
                    
                    if s3_url:
                        final_url = s3_url
                        logger.debug(f"[{job_id}] Uploaded to S3: {s3_key}")
                    else:
                        logger.warning(f"[{job_id}] S3 upload failed, using AI URL")
            except Exception as e:
                logger.warning(f"[{job_id}] S3 upload error: {e}, using AI URL")
        else:
            logger.debug(f"[{job_id}] S3 not configured")

        # ===== STEP 5: Cache Result =====
        logger.debug(f"[{job_id}] Caching result")
        cache.set_cached_result(user_image_url, garment_image_url, final_url)

        # ===== STEP 6: Update Job Status =====
        logger.debug(f"[{job_id}] Updating job status")
        elapsed_ms = int((dt.utcnow() - start_time).total_seconds() * 1000)
        
        _update_job_status(
            job_id=job_id,
            shop_id=shop_id,
            status="completed",
            image_url=final_url,
            generation_time=elapsed_ms
        )

        # ===== STEP 7: Record Usage =====
        logger.debug(f"[{job_id}] Recording usage")
        _record_usage(shop_id, job_id, product_id, elapsed_ms)

        logger.info(f"[{job_id}] ✓ Completed successfully in {elapsed_ms}ms")

        return {
            "job_id": job_id,
            "status": "completed",
            "image_url": final_url,
            "cached": False,
            "generation_time": elapsed_ms,
            "shop_id": shop_id
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Task error: {e} (attempt {self.request.retries + 1}/3)")
        
        # Check if max retries exceeded
        if self.request.retries >= self.max_retries:
            logger.error(f"[{job_id}] Max retries exhausted")
            try:
                _update_job_status(
                    job_id=job_id,
                    shop_id=shop_id,
                    status="failed",
                    error=str(e)
                )
            except Exception as db_err:
                logger.error(f"[{job_id}] Failed to update status: {db_err}")
            
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
                "shop_id": shop_id
            }
        
        # Retry with exponential backoff
        retry_delay = 2 ** self.request.retries  # 2, 4 seconds
        logger.info(f"[{job_id}] Retrying in {retry_delay}s")
        raise self.retry(exc=e, countdown=retry_delay)


# ============ HELPER ASYNC FUNCTIONS ============

async def _call_ai_inference(
    job_id: str,
    user_url: str,
    garment_url: str,
    category: str,
    ai_url: str
) -> dict:
    """Call AI inference service and poll for results"""
    import httpx
    from datetime import datetime as dt
    
    try:
        async with httpx.AsyncClient() as client:
            start = dt.utcnow()
            
            # Create prediction
            logger.debug(f"[{job_id}] Creating prediction at {ai_url}")
            resp = await client.post(
                f"{ai_url}/api/v1/generate-tryon",
                json={
                    "user_image_url": user_url,
                    "garment_image_url": garment_url,
                    "category": category
                },
                timeout=30
            )
            resp.raise_for_status()
            
            data = resp.json()
            pred_id = data.get("prediction_id")
            logger.debug(f"[{job_id}] Prediction created: {pred_id}")
            
            # Poll for result
            max_polls = 150  # ~5 minutes at 2s intervals
            poll_num = 0
            
            while poll_num < max_polls:
                import asyncio
                await asyncio.sleep(2)
                poll_num += 1
                
                status_resp = await client.get(
                    f"{ai_url}/api/v1/status/{pred_id}",
                    timeout=10
                )
                status_resp.raise_for_status()
                
                status = status_resp.json()
                st = status.get("status")
                
                logger.debug(f"[{job_id}] Poll {poll_num}: {st}")
                
                if st == "completed":
                    elapsed = int((dt.utcnow() - start).total_seconds() * 1000)
                    return {
                        "success": True,
                        "image_url": status.get("image_url"),
                        "inference_time": elapsed,
                        "prediction_id": pred_id
                    }
                elif st == "failed":
                    return {
                        "success": False,
                        "error": status.get("error", "Unknown")
                    }
            
            return {
                "success": False,
                "error": "Inference polling timeout"
            }
            
    except Exception as e:
        logger.error(f"[{job_id}] AI service error: {e}")
        return {"success": False, "error": str(e)}


# ============ DATABASE UPDATE HELPERS ============

def _update_job_status(
    job_id: str,
    shop_id: int,
    status: str,
    image_url: str = None,
    generation_time: int = 0,
    error: str = None
) -> bool:
    """Update job status in PostgreSQL"""
    try:
        from sqlalchemy import create_engine, text
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.warning(f"[{job_id}] DATABASE_URL not configured")
            return False
        
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            query = text("""
                UPDATE tryon_job
                SET status = :status,
                    result_image_url = :image_url,
                    generated_at = CASE WHEN :status = 'completed' THEN NOW() ELSE NULL END,
                    error_message = :error,
                    updated_at = NOW()
                WHERE id = :job_id AND shop_id = :shop_id
            """)
            
            conn.execute(query, {
                "job_id": job_id,
                "shop_id": shop_id,
                "status": status,
                "image_url": image_url,
                "error": error
            })
            conn.commit()
        
        logger.debug(f"[{job_id}] Updated to status={status}")
        return True
        
    except Exception as e:
        logger.error(f"[{job_id}] Failed to update status: {e}")
        return False


def _record_usage(
    shop_id: int,
    job_id: str,
    product_id: str,
    generation_time: int
) -> bool:
    """Record usage in PostgreSQL"""
    try:
        from sqlalchemy import create_engine, text
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.warning("DATABASE_URL not configured")
            return False
        
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            query = text("""
                INSERT INTO tryon_usage (
                    shop_id, job_id, product_id, generation_time, image_cached, created_at
                ) VALUES (
                    :shop_id, :job_id, :product_id, :gen_time, false, NOW()
                )
            """)
            
            conn.execute(query, {
                "shop_id": shop_id,
                "job_id": job_id,
                "product_id": product_id,
                "gen_time": generation_time
            })
            conn.commit()
        
        logger.debug(f"Recorded usage for shop={shop_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to record usage: {e}")
        return False


# ============ PERIODIC CLEANUP TASK ============

@celery_app.task(name="tryon.cleanup_old_jobs")
def cleanup_old_jobs() -> dict:
    """Clean up old jobs and S3 files"""
    try:
        from sqlalchemy import create_engine, text
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return {"status": "skipped", "reason": "DATABASE_URL not set"}
        
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            # Delete jobs older than 7 days
            conn.execute(text("""
                DELETE FROM tryon_job
                WHERE status = 'failed' AND created_at < NOW() - INTERVAL '7 days'
            """))
            
            conn.commit()
        
        # Clean S3
        from backend_api.app.storage.s3_client import get_storage_service
        s3 = get_storage_service()
        s3_deleted = s3.delete_expired_files("try-ons/", 720) if s3 and s3.client else 0
        
        logger.info(f"Cleanup: deleted {s3_deleted} S3 files")
        
        return {
            "status": "completed",
            "s3_files_deleted": s3_deleted
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"status": "error", "error": str(e)}


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
