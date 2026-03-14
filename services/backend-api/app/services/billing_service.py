"""Billing and plan management service"""

import logging
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BillingService:
    """Manages billing plans and generation limits"""
    
    # Plan configurations
    PLANS = {
        "free": {"monthly_limit": 50, "price": 0},
        "pro": {"monthly_limit": 500, "price": 49},
        "enterprise": {"monthly_limit": 5000, "price": 299},
    }
    
    @staticmethod
    def get_store_plan(session: Session, shop_id: int) -> Optional[dict]:
        """
        Get store's current plan
        
        Args:
            session: Database session
            shop_id: Shopify store ID
            
        Returns:
            Plan dict with {plan, limit, used, remaining}
        """
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT plan, generation_limit, used_generations 
                FROM store_plans WHERE shop_id = :shop_id
            """)
            
            result = session.execute(query, {"shop_id": shop_id}).first()
            
            if not result:
                # Default to free plan if not set
                BillingService._create_default_plan(session, shop_id)
                plan = "free"
                limit = BillingService.PLANS["free"]["monthly_limit"]
                used = 0
            else:
                plan, limit, used = result
            
            return {
                "plan": plan,
                "monthly_limit": limit,
                "used_generations": used,
                "remaining": max(0, limit - used),
                "price": BillingService.PLANS.get(plan, {}).get("price", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get store plan: {e}")
            return None
    
    @staticmethod
    def can_generate(session: Session, shop_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if store can generate a try-on
        
        Args:
            session: Database session
            shop_id: Shopify store ID
            
        Returns:
            Tuple of (can_generate: bool, error_message: Optional[str])
        """
        try:
            plan = BillingService.get_store_plan(session, shop_id)
            
            if not plan:
                return False, "Unable to determine plan"
            
            if plan["remaining"] <= 0:
                return False, f"Monthly generation limit ({plan['monthly_limit']}) reached. Upgrade to {plan['plan']} plan."
            
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to check generation eligibility: {e}")
            return False, "Unable to check plan limits"
    
    @staticmethod
    def increment_usage(session: Session, shop_id: int) -> bool:
        """
        Increment usage counter for shop
        
        Args:
            session: Database session
            shop_id: Shopify store ID
            
        Returns:
            True if successful
        """
        try:
            from sqlalchemy import text
            
            query = text("""
                UPDATE store_plans
                SET used_generations = used_generations + 1,
                    updated_at = NOW()
                WHERE shop_id = :shop_id
                RETURNING used_generations
            """)
            
            result = session.execute(query, {"shop_id": shop_id}).first()
            session.commit()
            
            if result:
                logger.info(f"Incremented usage for shop={shop_id}, now at {result[0]}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to increment usage: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def reset_monthly_usage(session: Session, shop_id: int) -> bool:
        """
        Reset monthly usage counter (called on month boundary)
        
        Args:
            session: Database session
            shop_id: Shopify store ID
            
        Returns:
            True if successful
        """
        try:
            from sqlalchemy import text
            
            query = text("""
                UPDATE store_plans
                SET used_generations = 0,
                    month_start_date = NOW(),
                    updated_at = NOW()
                WHERE shop_id = :shop_id
            """)
            
            session.execute(query, {"shop_id": shop_id})
            session.commit()
            
            logger.info(f"Reset monthly usage for shop={shop_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset monthly usage: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def upgrade_plan(session: Session, shop_id: int, new_plan: str) -> bool:
        """
        Upgrade store plan
        
        Args:
            session: Database session
            shop_id: Shopify store ID
            new_plan: New plan name (free, pro, enterprise)
            
        Returns:
            True if successful
        """
        try:
            if new_plan not in BillingService.PLANS:
                logger.warning(f"Invalid plan: {new_plan}")
                return False
            
            from sqlalchemy import text
            
            new_limit = BillingService.PLANS[new_plan]["monthly_limit"]
            
            query = text("""
                UPDATE store_plans
                SET plan = :plan,
                    generation_limit = :limit,
                    used_generations = 0,
                    month_start_date = NOW(),
                    updated_at = NOW()
                WHERE shop_id = :shop_id
            """)
            
            session.execute(query, {
                "plan": new_plan,
                "limit": new_limit,
                "shop_id": shop_id
            })
            session.commit()
            
            logger.info(f"Upgraded shop={shop_id} to plan={new_plan}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upgrade plan: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def _create_default_plan(session: Session, shop_id: int) -> bool:
        """Create default free plan for new shop"""
        try:
            from sqlalchemy import text
            
            query = text("""
                INSERT INTO store_plans (shop_id, plan, generation_limit, used_generations, month_start_date)
                VALUES (:shop_id, :plan, :limit, 0, NOW())
                ON CONFLICT (shop_id) DO NOTHING
            """)
            
            session.execute(query, {
                "shop_id": shop_id,
                "plan": "free",
                "limit": BillingService.PLANS["free"]["monthly_limit"]
            })
            session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create default plan: {e}")
            session.rollback()
            return False


# Global service instance
_billing_service = None


def get_billing_service() -> BillingService:
    """Get billing service"""
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService()
    return _billing_service
