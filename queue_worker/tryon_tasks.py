"""
Try-On Generation Celery Tasks

Async tasks for:
- Try-on ML model inference
- Image processing
- Result caching
- Database updates
- Error handling
"""

import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional

from celery import shared_task
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


# ============ CELERY TASK CONFIG ============

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=900,  # 15 minutes hard limit
    soft_time_limit=840  # 14 minutes soft limit
)
def generate_tryon_task(
    self,
    job_id: str,
    shop_id: int,
    product_id: str,
    user_image_url: str,
    garment_image_url: str,
    category: str = "upper_body"
) -> Dict:
    """
    Main async try-on generation task.
    
    Pipeline:
    1. Download images
    2. Call ML model
    3. Post-process result
    4. Upload to storage
    5. Update database
    
    Args:
        job_id: Unique job identifier
        shop_id: Shopify store ID
        product_id: Product ID
        user_image_url: URL to user's image
        garment_image_url: URL to garment image
        category: Clothing category
    
    Returns:
        Dict with result_url and metadata
    """
    
    start_time = time.time()
    
    try:
        logger.info(f"[{job_id}] Starting try-on generation")
        
        # ===== UPDATE STATUS =====
        _update_job_status(job_id, "processing")
        
        # ===== DOWNLOAD IMAGES =====
        logger.info(f"[{job_id}] Downloading images")
        user_image = _download_image(user_image_url)
        garment_image = _download_image(garment_image_url)
        
        if not user_image or not garment_image:
            raise ValueError("Failed to download images")
        
        # ===== RUN ML MODEL =====
        logger.info(f"[{job_id}] Running ML model")
        result_image = _run_tryon_model(
            user_image=user_image,
            garment_image=garment_image,
            category=category
        )
        
        if result_image is None:
            raise ValueError("ML model returned None")
        
        # ===== UPLOAD RESULT =====
        logger.info(f"[{job_id}] Uploading result")
        result_url = _upload_result(
            job_id=job_id,
            shop_id=shop_id,
            image_data=result_image
        )
        
        # ===== UPDATE DATABASE =====
        generation_time = int((time.time() - start_time) * 1000)  # ms
        
        logger.info(f"[{job_id}] Updating database (took {generation_time}ms)")
        _update_job_success(
            job_id=job_id,
            result_url=result_url,
            generation_time=generation_time
        )
        
        # ===== INCREMENT BILLING =====
        _increment_usage(shop_id=shop_id)
        
        logger.info(f"[{job_id}] Try-on generation completed in {generation_time}ms")
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result_url": result_url,
            "generation_time_ms": generation_time
        }
        
    except Exception as e:
        logger.exception(f"[{job_id}] Error in try-on generation: {e}")
        
        # ===== RETRY LOGIC =====
        retry_count = self.request.retries
        
        if retry_count < self.max_retries:
            logger.info(f"[{job_id}] Retrying (attempt {retry_count + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (retry_count + 1))  # Exponential backoff
        
        # ===== MARK AS FAILED =====
        logger.error(f"[{job_id}] All retries exhausted, marking as failed")
        _update_job_failure(job_id, str(e))
        
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
            "generation_time_ms": int((time.time() - start_time) * 1000)
        }


# ============ HELPER FUNCTIONS ============

def _update_job_status(job_id: str, status: str) -> None:
    """Update job status in database"""
    try:
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE tryon_job
                SET status = :status, updated_at = NOW()
                WHERE id = :job_id
            """), {"status": status, "job_id": job_id})
            conn.commit()
            
    except Exception as e:
        logger.error(f"[{job_id}] Failed to update status to {status}: {e}")


def _download_image(url: str) -> Optional[bytes]:
    """Download image from URL"""
    try:
        import httpx
        
        client = httpx.Client(timeout=30.0)
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        
        return response.content
        
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        return None


def _run_tryon_model(
    user_image: bytes,
    garment_image: bytes,
    category: str
) -> Optional[bytes]:
    """
    Run the ML model for try-on generation.
    
    In production, this calls:
    - inference-service (HuggingFace model)
    - Or GPT-4 Vision for better quality
    """
    try:
        import httpx
        from io import BytesIO
        
        # ===== OPTION 1: INFERENCE SERVICE =====
        inference_url = os.getenv("INFERENCE_SERVICE_URL", "http://inference-service:8000")
        
        logger.info(f"Calling inference service: {inference_url}")
        
        client = httpx.Client(timeout=120.0)
        
        files = {
            'user_image': ('user.png', user_image, 'image/png'),
            'garment_image': ('garment.png', garment_image, 'image/png'),
        }
        data = {
            'category': category
        }
        
        response = client.post(
            f"{inference_url}/v1/tryon",
            files=files,
            data=data
        )
        
        if response.status_code != 200:
            logger.error(f"Inference service returned {response.status_code}: {response.text}")
            return None
        
        result = response.json()
        
        # Get image from response
        if isinstance(result, dict) and 'image_url' in result:
            # If service returned URL, download it
            img_response = client.get(result['image_url'])
            return img_response.content
        elif isinstance(result, bytes):
            return result
        else:
            logger.error(f"Unexpected response format: {result}")
            return None
            
    except Exception as e:
        logger.error(f"ML model error: {e}")
        return None


def _upload_result(
    job_id: str,
    shop_id: int,
    image_data: bytes
) -> str:
    """
    Upload result image to storage.
    
    Uses S3 or cloud storage configured via env vars.
    """
    try:
        import io
        
        # ===== OPTION 1: AWS S3 =====
        storage_type = os.getenv("STORAGE_TYPE", "s3").lower()
        
        if storage_type == "s3":
            return _upload_to_s3(job_id, shop_id, image_data)
        elif storage_type == "gcs":
            return _upload_to_gcs(job_id, shop_id, image_data)
        elif storage_type == "local":
            return _upload_to_local(job_id, shop_id, image_data)
        else:
            logger.error(f"Unknown storage type: {storage_type}")
            raise ValueError(f"Unknown storage type: {storage_type}")
            
    except Exception as e:
        logger.error(f"Failed to upload result: {e}")
        raise


def _upload_to_s3(job_id: str, shop_id: int, image_data: bytes) -> str:
    """Upload to AWS S3"""
    try:
        import boto3
        from datetime import datetime
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        
        bucket = os.getenv("S3_BUCKET", "digicloset-tryon-results")
        
        # S3 key structure: shops/{shop_id}/tryon/{job_id}.png
        key = f"shops/{shop_id}/tryon/{job_id}.png"
        
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=image_data,
            ContentType='image/png',
            CacheControl='public, max-age=31536000'  # Cache for 1 year
        )
        
        # Return public URL or signed URL
        url = f"https://{bucket}.s3.amazonaws.com/{key}"
        logger.info(f"[{job_id}] Uploaded to S3: {url}")
        
        return url
        
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise


def _upload_to_gcs(job_id: str, shop_id: int, image_data: bytes) -> str:
    """Upload to Google Cloud Storage"""
    try:
        from google.cloud import storage
        
        client = storage.Client()
        bucket = client.bucket(os.getenv("GCS_BUCKET", "digicloset-tryon-results"))
        
        blob = bucket.blob(f"shops/{shop_id}/tryon/{job_id}.png")
        blob.upload_from_string(image_data, content_type='image/png')
        
        # Make public if configured
        if os.getenv("GCS_PUBLIC") == "true":
            blob.make_public()
        
        url = blob.public_url
        logger.info(f"[{job_id}] Uploaded to GCS: {url}")
        
        return url
        
    except Exception as e:
        logger.error(f"GCS upload failed: {e}")
        raise


def _upload_to_local(job_id: str, shop_id: int, image_data: bytes) -> str:
    """Upload to local filesystem (dev only)"""
    try:
        upload_dir = os.getenv("LOCAL_UPLOAD_DIR", "/tmp/tryon_results")
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{job_id}.png"
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        # Return local URL
        url = f"/uploads/{filename}"
        logger.info(f"[{job_id}] Uploaded locally: {url}")
        
        return url
        
    except Exception as e:
        logger.error(f"Local upload failed: {e}")
        raise


def _update_job_success(
    job_id: str,
    result_url: str,
    generation_time: int
) -> None:
    """Update job with successful result"""
    try:
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE tryon_job
                SET
                    status = 'completed',
                    result_image_url = :url,
                    generation_time_ms = :time,
                    updated_at = NOW()
                WHERE id = :job_id
            """), {
                "url": result_url,
                "time": generation_time,
                "job_id": job_id
            })
            conn.commit()
            
    except Exception as e:
        logger.error(f"[{job_id}] Failed to update job success: {e}")


def _update_job_failure(job_id: str, error_message: str) -> None:
    """Update job with failure"""
    try:
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE tryon_job
                SET
                    status = 'failed',
                    error_message = :error,
                    updated_at = NOW()
                WHERE id = :job_id
            """), {
                "error": error_message,
                "job_id": job_id
            })
            conn.commit()
            
    except Exception as e:
        logger.error(f"[{job_id}] Failed to update job failure: {e}")


def _increment_usage(shop_id: int) -> None:
    """Increment usage counter for billing"""
    try:
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE store_plans
                SET used_generations = used_generations + 1
                WHERE shop_id = :shop_id
            """), {"shop_id": shop_id})
            conn.commit()
            
    except Exception as e:
        logger.error(f"Failed to increment usage for shop {shop_id}: {e}")
    


# ============ BATCH OPERATIONS ============

@shared_task
def cleanup_old_jobs(days: int = 30) -> None:
    """
    Cleanup old completed/failed jobs.
    
    Runs daily cron job.
    """
    try:
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                DELETE FROM tryon_job
                WHERE
                    status IN ('completed', 'failed')
                    AND updated_at < NOW() - INTERVAL :days DAY
                RETURNING id
            """), {"days": days})
            
            deleted_count = len(result.fetchall())
            logger.info(f"Cleaned up {deleted_count} jobs older than {days} days")
            
            conn.commit()
            
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")


@shared_task
def reset_monthly_limits() -> None:
    """Reset monthly usage limits. Runs on 1st of each month."""
    try:
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE store_plans
                SET used_generations = 0
                WHERE billing_cycle_type = 'monthly'
            """))
            
            logger.info(f"Reset monthly limits for {result.rowcount} stores")
            conn.commit()
            
    except Exception as e:
        logger.error(f"Monthly reset failed: {e}")
