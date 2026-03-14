"""Service for tracking per-store usage"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """Tracks try-on generation usage per store"""
    
    @staticmethod
    def record_generation(
        session: Session,
        shop_id: int,
        job_id: str,
        product_id: str,
        generation_time: int,
        image_cached: bool = False,
        s3_url: Optional[str] = None
    ) -> bool:
        """
        Record a successful try-on generation
        
        Args:
            session: Database session
            shop_id: Shopify store ID
            job_id: Celery job ID
            product_id: Product being tried on
            generation_time: Time taken in milliseconds
            image_cached: Whether result was from cache
            s3_url: S3 URL of generated image
            
        Returns:
            True if recorded successfully
        """
        try:
            # Import here to avoid circular imports
            from sqlalchemy import text
            
            # Record usage
            query = text("""
                INSERT INTO tryon_usage (
                    shop_id, job_id, product_id, 
                    generation_time, image_cached, s3_url, created_at
                ) VALUES (
                    :shop_id, :job_id, :product_id,
                    :generation_time, :image_cached, :s3_url, :created_at
                )
            """)
            
            session.execute(query, {
                "shop_id": shop_id,
                "job_id": job_id,
                "product_id": product_id,
                "generation_time": generation_time,
                "image_cached": image_cached,
                "s3_url": s3_url,
                "created_at": datetime.utcnow()
            })
            session.commit()
            
            logger.info(f"Recorded usage for shop={shop_id}, job={job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def get_usage_count(
        session: Session,
        shop_id: int,
        time_period_hours: int = 24
    ) -> int:
        """
        Get usage count for a shop in time period
        
        Args:
            session: Database session
            shop_id: Shopify store ID
            time_period_hours: Hours to look back (default: 24)
            
        Returns:
            Number of generations in period
        """
        try:
            from sqlalchemy import text, func
            
            query = text("""
                SELECT COUNT(*) as count FROM tryon_usage
                WHERE shop_id = :shop_id
                AND created_at >= NOW() - INTERVAL ':period hours'
            """)
            
            result = session.execute(query, {
                "shop_id": shop_id,
                "period": time_period_hours
            }).first()
            
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get usage count: {e}")
            return 0
    
    @staticmethod
    def get_monthly_usage(session: Session, shop_id: int) -> int:
        """Get current month usage"""
        return UsageTrackingService.get_usage_count(session, shop_id, time_period_hours=720)


# Global service instance
_usage_service = None


def get_usage_service() -> UsageTrackingService:
    """Get usage tracking service"""
    global _usage_service
    if _usage_service is None:
        _usage_service = UsageTrackingService()
    return _usage_service
