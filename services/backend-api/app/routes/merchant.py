"""
Merchant Routes

Merchant authentication, profile, settings
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class MerchantProfile(BaseModel):
    """Merchant profile"""
    shop_id: str
    shop_name: str
    email: str
    created_at: datetime
    plan: str


class SettingsUpdate(BaseModel):
    """Settings update"""
    widget_enabled: bool = True
    webhook_url: str = None


@router.get("/merchant/profile", response_model=MerchantProfile)
async def get_merchant_profile(shop_id: str = None):
    """Get merchant profile"""
    try:
        logger.info(f"Profile request for shop: {shop_id}")
        
        return MerchantProfile(
            shop_id=shop_id,
            shop_name="Sample Store",
            email="merchant@example.com",
            created_at=datetime.now(),
            plan="pro"
        )
    except Exception as e:
        logger.exception(f"Failed to get profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.post("/merchant/settings")
async def update_settings(shop_id: str = None, settings: SettingsUpdate = None):
    """Update merchant settings"""
    try:
        logger.info(f"Settings update for shop: {shop_id}")
        
        return {
            "status": "updated",
            "shop_id": shop_id
        }
    except Exception as e:
        logger.exception(f"Failed to update settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.post("/merchant/oauth/callback")
async def handle_oauth_callback(code: str = None, shop: str = None):
    """Handle Shopify OAuth callback"""
    try:
        logger.info(f"OAuth callback for shop: {shop}")
        
        # Exchange code for access token
        # Store access token in database
        
        return {
            "status": "authenticated",
            "shop": shop,
            "access_token": "***"
        }
    except Exception as e:
        logger.exception(f"OAuth callback failed: {str(e)}")
        raise HTTPException(status_code=500, detail="OAuth failed")
