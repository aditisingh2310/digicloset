"""
Merchant ROI Dashboard API Routes.

Provides endpoints for merchants to view their ROI metrics, outfit performance,
and business intelligence data. All endpoints are tenant-isolated.

Endpoints:
- GET /metrics/summary: Overall performance summary
- GET /metrics/aov-comparison: AOV comparison with/without outfits
- GET /metrics/outfit-performance: Top performing outfits
- GET /metrics/revenue-attribution: Revenue attribution over time
- GET /metrics/usage-limits: Current usage vs limits
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from app.middleware.tenant_isolation import require_tenant, get_shop_id
from app.services.revenue_attribution import revenue_attribution
from app.services.ai_metering import ai_metering
from app.services.observability import observability
from app.utils.errors import APIError, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


# Response Models
class ROISummary(BaseModel):
    """Overall ROI summary for a merchant."""
    shop_id: str
    period_days: int
    total_revenue_influenced: float = Field(..., description="Total revenue attributed to outfits")
    total_orders_influenced: int = Field(..., description="Orders influenced by outfits")
    average_order_value: float = Field(..., description="Average order value")
    outfit_conversion_rate: float = Field(..., description="Outfit click to purchase conversion")
    top_outfit_revenue: float = Field(..., description="Revenue from top performing outfit")
    total_outfits_generated: int = Field(..., description="Total outfits generated")
    total_outfit_views: int = Field(..., description="Total outfit views")
    total_outfit_clicks: int = Field(..., description="Total outfit clicks")
    roi_percentage: float = Field(..., description="Return on investment percentage")


class AOVComparison(BaseModel):
    """AOV comparison with and without outfit influence."""
    shop_id: str
    period_days: int
    orders_with_outfits: int = Field(..., description="Orders influenced by outfits")
    orders_without_outfits: int = Field(..., description="Orders not influenced by outfits")
    aov_with_outfits: float = Field(..., description="Average order value for influenced orders")
    aov_without_outfits: float = Field(..., description="Average order value for non-influenced orders")
    aov_lift_percentage: float = Field(..., description="Percentage increase in AOV")
    total_revenue_with_outfits: float = Field(..., description="Total revenue from influenced orders")
    total_revenue_without_outfits: float = Field(..., description="Total revenue from non-influenced orders")


class OutfitPerformance(BaseModel):
    """Performance metrics for an outfit."""
    outfit_id: str
    created_at: datetime
    views: int = Field(..., description="Number of times viewed")
    clicks: int = Field(..., description="Number of times clicked")
    purchases: int = Field(..., description="Number of purchases attributed")
    revenue_influenced: float = Field(..., description="Revenue attributed to this outfit")
    conversion_rate: float = Field(..., description="Click to purchase conversion rate")
    last_updated: datetime


class UsageLimits(BaseModel):
    """Current usage vs plan limits."""
    shop_id: str
    current_plan: str = Field(..., description="Current subscription plan")
    ai_requests_used: int = Field(..., description="AI requests used this month")
    ai_requests_limit: int = Field(..., description="Monthly AI request limit")
    outfits_generated_used: int = Field(..., description="Outfits generated this month")
    outfits_generated_limit: int = Field(..., description="Monthly outfit generation limit")
    storage_used_mb: float = Field(..., description="Storage used in MB")
    storage_limit_mb: float = Field(..., description="Storage limit in MB")
    usage_percentage: float = Field(..., description="Overall usage percentage")
    upgrade_recommended: bool = Field(..., description="Whether upgrade is recommended")
    days_until_reset: int = Field(..., description="Days until usage resets")


class RevenueAttributionTimeline(BaseModel):
    """Revenue attribution data over time."""
    shop_id: str
    period_days: int
    timeline: List[Dict[str, Any]] = Field(..., description="Daily revenue attribution data")


@router.get("/summary", response_model=ROISummary)
async def get_roi_summary(
    shop_id: str = Depends(require_tenant),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
) -> ROISummary:
    """
    Get overall ROI summary for the merchant.

    Returns key metrics including revenue influenced, conversion rates,
    and outfit performance over the specified period.
    """
    try:
        # Get revenue attribution data
        revenue_data = await revenue_attribution.calculate_revenue_influenced(
            shop_id=shop_id,
            days=days
        )

        # Get event counts from observability
        event_counts = await observability.get_event_counts(
            shop_id=shop_id,
            days=days
        )

        # Get outfit performance data
        outfit_performance = await observability.get_outfit_performance(
            shop_id=shop_id,
            limit=1  # Just need the top one for summary
        )

        # Calculate metrics
        total_revenue = revenue_data.get("total_revenue_influenced", 0.0)
        total_orders = revenue_data.get("total_orders_influenced", 0)

        outfit_views = event_counts.get("outfit_viewed", 0)
        outfit_clicks = event_counts.get("outfit_clicked", 0)
        outfits_generated = event_counts.get("outfit_generated", 0)

        # Calculate conversion rate
        conversion_rate = outfit_clicks / outfit_views if outfit_views > 0 else 0.0

        # Calculate AOV
        aov = total_revenue / total_orders if total_orders > 0 else 0.0

        # Get top outfit revenue
        top_outfit_revenue = 0.0
        if outfit_performance:
            top_outfit_revenue = outfit_performance[0].get("revenue_influenced", 0.0)

        # Calculate ROI (simplified - revenue influenced vs estimated costs)
        # This is a placeholder - in real implementation, you'd track actual costs
        estimated_cost_per_outfit = 0.01  # $0.01 per outfit generated
        total_costs = outfits_generated * estimated_cost_per_outfit
        roi_percentage = ((total_revenue - total_costs) / total_costs * 100) if total_costs > 0 else 0.0

        return ROISummary(
            shop_id=shop_id,
            period_days=days,
            total_revenue_influenced=total_revenue,
            total_orders_influenced=total_orders,
            average_order_value=aov,
            outfit_conversion_rate=conversion_rate,
            top_outfit_revenue=top_outfit_revenue,
            total_outfits_generated=outfits_generated,
            total_outfit_views=outfit_views,
            total_outfit_clicks=outfit_clicks,
            roi_percentage=roi_percentage,
        )

    except Exception as e:
        logger.error(f"Failed to get ROI summary for shop {shop_id}: {e}")
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve ROI summary: {str(e)}"
        )


@router.get("/aov-comparison", response_model=AOVComparison)
async def get_aov_comparison(
    shop_id: str = Depends(require_tenant),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
) -> AOVComparison:
    """
    Get AOV comparison between orders influenced by outfits vs not influenced.

    Helps merchants understand the incremental value outfits provide.
    """
    try:
        # Get detailed revenue attribution data
        revenue_data = await revenue_attribution.calculate_revenue_influenced(
            shop_id=shop_id,
            days=days,
            include_order_details=True
        )

        # Extract order data
        orders_with_outfits = revenue_data.get("orders_with_outfits", [])
        orders_without_outfits = revenue_data.get("orders_without_outfits", [])

        # Calculate AOVs
        revenue_with = sum(order.get("revenue", 0) for order in orders_with_outfits)
        revenue_without = sum(order.get("revenue", 0) for order in orders_without_outfits)

        count_with = len(orders_with_outfits)
        count_without = len(orders_without_outfits)

        aov_with = revenue_with / count_with if count_with > 0 else 0.0
        aov_without = revenue_without / count_without if count_without > 0 else 0.0

        # Calculate lift
        aov_lift = ((aov_with - aov_without) / aov_without * 100) if aov_without > 0 else 0.0

        return AOVComparison(
            shop_id=shop_id,
            period_days=days,
            orders_with_outfits=count_with,
            orders_without_outfits=count_without,
            aov_with_outfits=aov_with,
            aov_without_outfits=aov_without,
            aov_lift_percentage=aov_lift,
            total_revenue_with_outfits=revenue_with,
            total_revenue_without_outfits=revenue_without,
        )

    except Exception as e:
        logger.error(f"Failed to get AOV comparison for shop {shop_id}: {e}")
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve AOV comparison: {str(e)}"
        )


@router.get("/outfit-performance", response_model=List[OutfitPerformance])
async def get_outfit_performance(
    shop_id: str = Depends(require_tenant),
    limit: int = Query(10, description="Number of top outfits to return", ge=1, le=50),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
) -> List[OutfitPerformance]:
    """
    Get performance metrics for top-performing outfits.

    Returns outfits sorted by revenue influenced, with view/click/purchase metrics.
    """
    try:
        # Get outfit performance from observability
        outfit_data = await observability.get_outfit_performance(
            shop_id=shop_id,
            limit=limit
        )

        # Get revenue attribution for each outfit
        performance_list = []
        for outfit in outfit_data:
            outfit_id = outfit.get("outfit_id")

            # Get revenue for this specific outfit
            revenue_data = await revenue_attribution.calculate_revenue_influenced(
                shop_id=shop_id,
                outfit_id=outfit_id,
                days=days
            )

            events = outfit.get("events", {})
            views = events.get("outfit_viewed", 0)
            clicks = events.get("outfit_clicked", 0)
            purchases = revenue_data.get("total_orders_influenced", 0)
            revenue = revenue_data.get("total_revenue_influenced", 0.0)

            conversion_rate = clicks / views if views > 0 else 0.0

            performance_list.append(OutfitPerformance(
                outfit_id=outfit_id,
                created_at=datetime.fromisoformat(outfit.get("created_at")),
                views=views,
                clicks=clicks,
                purchases=purchases,
                revenue_influenced=revenue,
                conversion_rate=conversion_rate,
                last_updated=datetime.fromisoformat(outfit.get("last_updated")),
            ))

        return performance_list

    except Exception as e:
        logger.error(f"Failed to get outfit performance for shop {shop_id}: {e}")
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve outfit performance: {str(e)}"
        )


@router.get("/revenue-attribution", response_model=RevenueAttributionTimeline)
async def get_revenue_attribution_timeline(
    shop_id: str = Depends(require_tenant),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
) -> RevenueAttributionTimeline:
    """
    Get revenue attribution data over time.

    Returns daily breakdown of revenue influenced by outfits.
    """
    try:
        # Get timeline data from revenue attribution service
        timeline_data = await revenue_attribution.get_revenue_timeline(
            shop_id=shop_id,
            days=days
        )

        return RevenueAttributionTimeline(
            shop_id=shop_id,
            period_days=days,
            timeline=timeline_data
        )

    except Exception as e:
        logger.error(f"Failed to get revenue attribution timeline for shop {shop_id}: {e}")
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve revenue attribution timeline: {str(e)}"
        )


@router.get("/usage-limits", response_model=UsageLimits)
async def get_usage_limits(
    shop_id: str = Depends(require_tenant),
) -> UsageLimits:
    """
    Get current usage vs plan limits.

    Shows how close the merchant is to hitting their plan limits.
    """
    try:
        # Get usage stats from AI metering
        usage_stats = await ai_metering.get_usage_stats(shop_id)

        # Get plan limits (this would typically come from a billing/subscription service)
        # For now, using placeholder values
        plan_limits = await _get_plan_limits(shop_id)

        # Calculate usage percentage
        ai_usage_pct = (usage_stats.get("requests", 0) / plan_limits["ai_requests_limit"]) * 100
        outfit_usage_pct = (usage_stats.get("outfits", 0) / plan_limits["outfits_generated_limit"]) * 100
        storage_usage_pct = (usage_stats.get("storage_mb", 0) / plan_limits["storage_limit_mb"]) * 100

        overall_usage = (ai_usage_pct + outfit_usage_pct + storage_usage_pct) / 3

        # Check if upgrade is recommended (over 80% usage)
        upgrade_recommended = overall_usage > 80

        # Calculate days until reset (simplified - assuming monthly reset)
        now = datetime.utcnow()
        next_reset = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        days_until_reset = (next_reset - now).days

        return UsageLimits(
            shop_id=shop_id,
            current_plan=plan_limits["plan_name"],
            ai_requests_used=usage_stats.get("requests", 0),
            ai_requests_limit=plan_limits["ai_requests_limit"],
            outfits_generated_used=usage_stats.get("outfits", 0),
            outfits_generated_limit=plan_limits["outfits_generated_limit"],
            storage_used_mb=usage_stats.get("storage_mb", 0.0),
            storage_limit_mb=plan_limits["storage_limit_mb"],
            usage_percentage=overall_usage,
            upgrade_recommended=upgrade_recommended,
            days_until_reset=days_until_reset,
        )

    except Exception as e:
        logger.error(f"Failed to get usage limits for shop {shop_id}: {e}")
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve usage limits: {str(e)}"
        )


async def _get_plan_limits(shop_id: str) -> Dict[str, Any]:
    """
    Get plan limits for a shop.

    In a real implementation, this would query a billing/subscription database.
    For now, returns placeholder values based on shop_id.
    """
    # Placeholder logic - in production, query your billing system
    if "premium" in shop_id.lower():
        return {
            "plan_name": "Premium",
            "ai_requests_limit": 50000,
            "outfits_generated_limit": 10000,
            "storage_limit_mb": 5000,
        }
    elif "pro" in shop_id.lower():
        return {
            "plan_name": "Pro",
            "ai_requests_limit": 10000,
            "outfits_generated_limit": 2000,
            "storage_limit_mb": 1000,
        }
    else:
        return {
            "plan_name": "Basic",
            "ai_requests_limit": 1000,
            "outfits_generated_limit": 200,
            "storage_limit_mb": 100,
        }
