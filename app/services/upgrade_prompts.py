"""
Intelligent Upgrade Prompts Service.

Provides non-blocking upgrade recommendations based on usage patterns,
plan limits, and business metrics. Helps merchants upgrade proactively.

Features:
- Plan limit monitoring
- Usage pattern analysis
- Intelligent upgrade suggestions
- Non-blocking recommendations
- Integration with metering and observability
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.services.ai_metering import ai_metering
from app.services.revenue_attribution import revenue_attribution

logger = logging.getLogger(__name__)


class PlanTier(str, Enum):
    """Available plan tiers."""
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class UpgradeTrigger(str, Enum):
    """Reasons for upgrade recommendations."""
    USAGE_LIMIT_APPROACHING = "usage_limit_approaching"
    USAGE_LIMIT_EXCEEDED = "usage_limit_exceeded"
    HIGH_ROI_OPPORTUNITY = "high_roi_opportunity"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    FEATURE_USAGE_INCREASE = "feature_usage_increase"
    REVENUE_GROWTH = "revenue_growth"


@dataclass
class UpgradeRecommendation:
    """Upgrade recommendation for a merchant."""
    shop_id: str
    recommended_plan: PlanTier
    current_plan: PlanTier
    trigger: UpgradeTrigger
    confidence_score: float  # 0-1, how confident we are in this recommendation
    estimated_monthly_value: float  # Estimated additional revenue per month
    reasons: List[str]
    suggested_features: List[str]
    urgency_level: str  # "low", "medium", "high", "critical"
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "shop_id": self.shop_id,
            "recommended_plan": self.recommended_plan.value,
            "current_plan": self.current_plan.value,
            "trigger": self.trigger.value,
            "confidence_score": self.confidence_score,
            "estimated_monthly_value": self.estimated_monthly_value,
            "reasons": self.reasons,
            "suggested_features": self.suggested_features,
            "urgency_level": self.urgency_level,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class PlanLimits:
    """Limits for a plan tier."""
    ai_requests_per_month: int
    outfits_generated_per_month: int
    storage_mb: float
    api_rate_limit_per_minute: int
    support_level: str  # "email", "chat", "phone"
    custom_branding: bool
    advanced_analytics: bool
    priority_processing: bool

    @classmethod
    def get_limits(cls, plan: PlanTier) -> 'PlanLimits':
        """Get limits for a plan tier."""
        limits = {
            PlanTier.BASIC: cls(
                ai_requests_per_month=1000,
                outfits_generated_per_month=200,
                storage_mb=100,
                api_rate_limit_per_minute=10,
                support_level="email",
                custom_branding=False,
                advanced_analytics=False,
                priority_processing=False,
            ),
            PlanTier.PRO: cls(
                ai_requests_per_month=10000,
                outfits_generated_per_month=2000,
                storage_mb=1000,
                api_rate_limit_per_minute=50,
                support_level="chat",
                custom_branding=True,
                advanced_analytics=True,
                priority_processing=False,
            ),
            PlanTier.PREMIUM: cls(
                ai_requests_per_month=50000,
                outfits_generated_per_month=10000,
                storage_mb=5000,
                api_rate_limit_per_minute=200,
                support_level="phone",
                custom_branding=True,
                advanced_analytics=True,
                priority_processing=True,
            ),
            PlanTier.ENTERPRISE: cls(
                ai_requests_per_month=200000,
                outfits_generated_per_month=50000,
                storage_mb=25000,
                api_rate_limit_per_minute=1000,
                support_level="dedicated",
                custom_branding=True,
                advanced_analytics=True,
                priority_processing=True,
            ),
        }
        return limits.get(plan, limits[PlanTier.BASIC])


class UpgradePromptsService:
    """
    Service for intelligent upgrade prompts and recommendations.

    Analyzes usage patterns, plan limits, and business metrics to provide
    timely upgrade recommendations without blocking functionality.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def check_plan_limits(
        self,
        shop_id: str,
        current_plan: PlanTier,
    ) -> Tuple[bool, Optional[UpgradeRecommendation]]:
        """
        Check if merchant is approaching or exceeding plan limits.

        Returns (upgrade_required, recommendation).
        Upgrade_required is True if any limit is exceeded or close to exceeded.
        """
        try:
            # Get current usage
            usage_stats = await ai_metering.get_usage_stats(shop_id)
            plan_limits = PlanLimits.get_limits(current_plan)

            # Check each limit
            ai_usage_pct = (usage_stats.get("requests", 0) / plan_limits.ai_requests_per_month) * 100
            outfit_usage_pct = (usage_stats.get("outfits", 0) / plan_limits.outfits_generated_per_month) * 100
            storage_usage_pct = (usage_stats.get("storage_mb", 0) / plan_limits.storage_mb) * 100

            # Determine if upgrade is needed
            upgrade_required = (
                ai_usage_pct >= 95 or  # Over 95% usage
                outfit_usage_pct >= 95 or
                storage_usage_pct >= 95 or
                ai_usage_pct >= 100 or  # Any limit exceeded
                outfit_usage_pct >= 100 or
                storage_usage_pct >= 100
            )

            if not upgrade_required:
                return False, None

            # Generate recommendation
            recommendation = await self._generate_limit_based_recommendation(
                shop_id, current_plan, usage_stats, plan_limits,
                ai_usage_pct, outfit_usage_pct, storage_usage_pct
            )

            return True, recommendation

        except Exception as e:
            self.logger.error(f"Failed to check plan limits for shop {shop_id}: {e}")
            return False, None

    async def get_upgrade_recommendation(
        self,
        shop_id: str,
        current_plan: PlanTier,
    ) -> Optional[UpgradeRecommendation]:
        """
        Get intelligent upgrade recommendation based on usage patterns and ROI.

        Analyzes multiple factors to provide personalized upgrade suggestions.
        """
        try:
            # Check basic limit-based recommendation
            limit_upgrade, limit_rec = await self.check_plan_limits(shop_id, current_plan)
            if limit_upgrade and limit_rec:
                return limit_rec

            # Analyze usage patterns for growth opportunities
            pattern_rec = await self._analyze_usage_patterns(shop_id, current_plan)
            if pattern_rec:
                return pattern_rec

            # Analyze ROI for value-based recommendations
            roi_rec = await self._analyze_roi_opportunities(shop_id, current_plan)
            if roi_rec:
                return roi_rec

            return None

        except Exception as e:
            self.logger.error(f"Failed to get upgrade recommendation for shop {shop_id}: {e}")
            return None

    async def _generate_limit_based_recommendation(
        self,
        shop_id: str,
        current_plan: PlanTier,
        usage_stats: Dict[str, Any],
        plan_limits: PlanLimits,
        ai_pct: float,
        outfit_pct: float,
        storage_pct: float,
    ) -> UpgradeRecommendation:
        """Generate recommendation based on limit usage."""

        # Determine recommended plan
        recommended_plan = self._get_next_plan_tier(current_plan)

        # Determine trigger and urgency
        max_usage = max(ai_pct, outfit_pct, storage_pct)
        if max_usage >= 100:
            trigger = UpgradeTrigger.USAGE_LIMIT_EXCEEDED
            urgency = "critical"
            confidence = 1.0
        elif max_usage >= 95:
            trigger = UpgradeTrigger.USAGE_LIMIT_APPROACHING
            urgency = "high"
            confidence = 0.9
        else:
            trigger = UpgradeTrigger.USAGE_LIMIT_APPROACHING
            urgency = "medium"
            confidence = 0.7

        # Build reasons
        reasons = []
        if ai_pct >= 80:
            reasons.append(f"AI requests at {ai_pct:.1f}% of limit ({usage_stats.get('requests', 0)}/{plan_limits.ai_requests_per_month})")
        if outfit_pct >= 80:
            reasons.append(f"Outfit generation at {outfit_pct:.1f}% of limit ({usage_stats.get('outfits', 0)}/{plan_limits.outfits_generated_per_month})")
        if storage_pct >= 80:
            reasons.append(f"Storage at {storage_pct:.1f}% of limit ({usage_stats.get('storage_mb', 0):.1f}MB/{plan_limits.storage_mb}MB)")

        # Estimate value (simplified)
        estimated_value = await self._estimate_upgrade_value(shop_id, current_plan, recommended_plan)

        # Suggested features based on usage
        suggested_features = []
        if ai_pct >= 80:
            suggested_features.extend(["Higher API limits", "Priority processing"])
        if outfit_pct >= 80:
            suggested_features.extend(["Advanced outfit algorithms", "Bulk generation"])
        if storage_pct >= 80:
            suggested_features.extend(["Increased storage", "Advanced analytics"])

        return UpgradeRecommendation(
            shop_id=shop_id,
            recommended_plan=recommended_plan,
            current_plan=current_plan,
            trigger=trigger,
            confidence_score=confidence,
            estimated_monthly_value=estimated_value,
            reasons=reasons,
            suggested_features=list(set(suggested_features)),  # Remove duplicates
            urgency_level=urgency,
            expires_at=datetime.utcnow() + timedelta(days=7),  # Expires in 7 days
        )

    async def _analyze_usage_patterns(
        self,
        shop_id: str,
        current_plan: PlanTier,
    ) -> Optional[UpgradeRecommendation]:
        """Analyze usage patterns for upgrade opportunities."""

        try:
            # Get usage over last 30 days
            usage_trend = await ai_metering.get_usage_trend(shop_id, days=30)

            if not usage_trend or len(usage_trend) < 7:
                return None

            # Calculate growth rate
            recent_week = sum(item.get("requests", 0) for item in usage_trend[-7:])
            previous_week = sum(item.get("requests", 0) for item in usage_trend[-14:-7])

            if previous_week == 0:
                growth_rate = 0
            else:
                growth_rate = ((recent_week - previous_week) / previous_week) * 100

            # If growing rapidly (>50% week over week), suggest upgrade
            if growth_rate > 50:
                recommended_plan = self._get_next_plan_tier(current_plan)
                estimated_value = await self._estimate_upgrade_value(shop_id, current_plan, recommended_plan)

                return UpgradeRecommendation(
                    shop_id=shop_id,
                    recommended_plan=recommended_plan,
                    current_plan=current_plan,
                    trigger=UpgradeTrigger.FEATURE_USAGE_INCREASE,
                    confidence_score=min(growth_rate / 100, 0.9),  # Cap at 0.9
                    estimated_monthly_value=estimated_value,
                    reasons=[f"Usage growing {growth_rate:.1f}% week over week"],
                    suggested_features=["Higher limits to support growth", "Advanced analytics"],
                    urgency_level="medium",
                    expires_at=datetime.utcnow() + timedelta(days=14),
                )

            return None

        except Exception as e:
            self.logger.error(f"Failed to analyze usage patterns for shop {shop_id}: {e}")
            return None

    async def _analyze_roi_opportunities(
        self,
        shop_id: str,
        current_plan: PlanTier,
    ) -> Optional[UpgradeRecommendation]:
        """Analyze ROI data for upgrade opportunities."""

        try:
            # Get revenue attribution data
            revenue_data = await revenue_attribution.calculate_revenue_influenced(
                shop_id=shop_id,
                days=30
            )

            total_revenue = revenue_data.get("total_revenue_influenced", 0)
            total_orders = revenue_data.get("total_orders_influenced", 0)

            # If generating significant revenue but on basic plan, suggest upgrade
            if (current_plan == PlanTier.BASIC and
                total_revenue > 1000 and  # Over $1000 in attributed revenue
                total_orders > 50):       # Over 50 influenced orders

                recommended_plan = PlanTier.PRO
                estimated_value = total_revenue * 0.1  # Estimate 10% additional value

                return UpgradeRecommendation(
                    shop_id=shop_id,
                    recommended_plan=recommended_plan,
                    current_plan=current_plan,
                    trigger=UpgradeTrigger.HIGH_ROI_OPPORTUNITY,
                    confidence_score=0.8,
                    estimated_monthly_value=estimated_value,
                    reasons=[
                        f"Generated ${total_revenue:.2f} in attributed revenue",
                        f"Influenced {total_orders} orders with current plan",
                        "Advanced features could increase ROI further"
                    ],
                    suggested_features=["Advanced analytics", "Priority processing", "Custom branding"],
                    urgency_level="medium",
                    expires_at=datetime.utcnow() + timedelta(days=30),
                )

            return None

        except Exception as e:
            self.logger.error(f"Failed to analyze ROI opportunities for shop {shop_id}: {e}")
            return None

    def _get_next_plan_tier(self, current_plan: PlanTier) -> PlanTier:
        """Get the next higher plan tier."""
        tier_order = [PlanTier.BASIC, PlanTier.PRO, PlanTier.PREMIUM, PlanTier.ENTERPRISE]
        try:
            current_index = tier_order.index(current_plan)
            if current_index < len(tier_order) - 1:
                return tier_order[current_index + 1]
        except ValueError:
            pass
        return PlanTier.PRO  # Default fallback

    async def _estimate_upgrade_value(
        self,
        shop_id: str,
        current_plan: PlanTier,
        recommended_plan: PlanTier,
    ) -> float:
        """Estimate the monthly value of upgrading."""

        try:
            # Get current revenue attribution
            revenue_data = await revenue_attribution.calculate_revenue_influenced(
                shop_id=shop_id,
                days=30
            )

            current_revenue = revenue_data.get("total_revenue_influenced", 0)

            # Estimate additional value based on plan upgrade
            # This is simplified - in reality, you'd use historical data and ML models
            if recommended_plan == PlanTier.PRO:
                multiplier = 1.2  # 20% increase
            elif recommended_plan == PlanTier.PREMIUM:
                multiplier = 1.5  # 50% increase
            elif recommended_plan == PlanTier.ENTERPRISE:
                multiplier = 2.0  # 100% increase
            else:
                multiplier = 1.1  # 10% increase

            return current_revenue * (multiplier - 1.0)

        except Exception as e:
            self.logger.error(f"Failed to estimate upgrade value for shop {shop_id}: {e}")
            return 0.0


# Global instance
upgrade_prompts = UpgradePromptsService()


# Helper functions
async def check_upgrade_required(shop_id: str, current_plan: PlanTier) -> bool:
    """
    Quick check if upgrade is required (limits exceeded or approaching).

    Returns True if upgrade should be recommended.
    """
    upgrade_required, _ = await upgrade_prompts.check_plan_limits(shop_id, current_plan)
    return upgrade_required


async def get_upgrade_prompt(shop_id: str, current_plan: PlanTier) -> Optional[Dict[str, Any]]:
    """
    Get upgrade prompt data for API responses.

    Returns recommendation dict or None if no upgrade needed.
    """
    recommendation = await upgrade_prompts.get_upgrade_recommendation(shop_id, current_plan)
    if recommendation:
        return recommendation.to_dict()
    return None
