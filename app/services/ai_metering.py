"""
Usage-Based AI Metering for Shopify multi-tenant FastAPI.

Tracks AI requests, tokens consumed, and outfits generated per shop.
Implements soft limits (warnings) and hard caps based on pricing tiers.

Features:
- Tenant-scoped usage tracking
- Multiple usage dimensions (requests, tokens, outfits)
- Pricing tier enforcement
- Soft limit warnings (80% threshold)
- Hard cap blocking
- Async-compatible with Redis backend
- Graceful degradation
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None

from app.core.redis_runtime import log_optional_redis_issue, redis_connection_kwargs

logger = logging.getLogger(__name__)


class PricingTier(str, Enum):
    """Available pricing tiers."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class TierLimits:
    """Usage limits for each pricing tier."""
    monthly_ai_requests: int
    monthly_tokens: int
    monthly_outfits: int
    concurrent_requests: int

    @classmethod
    def get_limits(cls, tier: PricingTier) -> 'TierLimits':
        """Get limits for a pricing tier."""
        limits = {
            PricingTier.FREE: cls(
                monthly_ai_requests=100,
                monthly_tokens=10_000,
                monthly_outfits=50,
                concurrent_requests=1,
            ),
            PricingTier.STARTER: cls(
                monthly_ai_requests=1_000,
                monthly_tokens=100_000,
                monthly_outfits=500,
                concurrent_requests=3,
            ),
            PricingTier.PROFESSIONAL: cls(
                monthly_ai_requests=10_000,
                monthly_tokens=1_000_000,
                monthly_outfits=5_000,
                concurrent_requests=10,
            ),
            PricingTier.ENTERPRISE: cls(
                monthly_ai_requests=100_000,
                monthly_tokens=10_000_000,
                monthly_outfits=50_000,
                concurrent_requests=50,
            ),
        }
        return limits.get(tier, limits[PricingTier.FREE])


@dataclass
class UsageMetrics:
    """Current usage metrics for a shop."""
    shop_id: str
    tier: PricingTier
    period_start: datetime

    # Current period usage
    ai_requests: int = 0
    tokens_consumed: int = 0
    outfits_generated: int = 0

    # Concurrent usage
    active_requests: int = 0

    # Limits
    monthly_ai_requests_limit: int = 0
    monthly_tokens_limit: int = 0
    monthly_outfits_limit: int = 0
    concurrent_requests_limit: int = 0

    last_updated: Optional[datetime] = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()

    @property
    def ai_requests_percentage(self) -> float:
        """Percentage of AI requests limit used."""
        return (self.ai_requests / max(self.monthly_ai_requests_limit, 1)) * 100

    @property
    def tokens_percentage(self) -> float:
        """Percentage of tokens limit used."""
        return (self.tokens_consumed / max(self.monthly_tokens_limit, 1)) * 100

    @property
    def outfits_percentage(self) -> float:
        """Percentage of outfits limit used."""
        return (self.outfits_generated / max(self.monthly_outfits_limit, 1)) * 100

    def is_near_limit(self, threshold: float = 80.0) -> bool:
        """Check if any usage is near the limit."""
        return (
            self.ai_requests_percentage >= threshold or
            self.tokens_percentage >= threshold or
            self.outfits_percentage >= threshold
        )

    def has_exceeded_limit(self) -> bool:
        """Check if any limit has been exceeded."""
        return (
            self.ai_requests >= self.monthly_ai_requests_limit or
            self.tokens_consumed >= self.monthly_tokens_limit or
            self.outfits_generated >= self.monthly_outfits_limit
        )

    def can_make_request(self) -> bool:
        """Check if a new AI request can be made."""
        return (
            self.ai_requests < self.monthly_ai_requests_limit and
            self.active_requests < self.concurrent_requests_limit
        )


@dataclass
class UsageEvent:
    """Represents a usage event."""
    shop_id: str
    event_type: str  # "ai_request", "token_usage", "outfit_generated"
    amount: int = 1
    timestamp: Optional[datetime] = None
    request_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class AIMeteringService:
    """
    Redis-backed AI usage metering service.

    Tracks usage per shop and enforces pricing tier limits.
    """

    def __init__(
        self,
        redis_url: str = None,
        redis_client: Any = None,
    ):
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
        self.redis_client = redis_client

        if not self.redis_client:
            if redis is None:
                log_optional_redis_issue(logger, "Redis package not available. Metering disabled.")
                self.redis_client = None
                return
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    **redis_connection_kwargs(),
                )
                # Test connection
                self.redis_client.ping()
                logger.info("AI metering service initialized successfully")
            except Exception as e:
                log_optional_redis_issue(logger, f"Failed to connect to Redis: {e}. Metering disabled.")
                self.redis_client = None

    def _get_usage_key(self, shop_id: str) -> str:
        """Generate Redis key for usage metrics."""
        return f"usage:{shop_id}"

    def _get_concurrent_key(self, shop_id: str) -> str:
        """Generate Redis key for concurrent request tracking."""
        return f"concurrent:{shop_id}"

    def _get_events_key(self, shop_id: str, date: datetime) -> str:
        """Generate Redis key for usage events."""
        date_str = date.strftime("%Y-%m-%d")
        return f"usage_events:{shop_id}:{date_str}"

    async def get_shop_tier(self, shop_id: str) -> PricingTier:
        """
        Get pricing tier for a shop.

        In production, this would query your billing database.
        For now, defaults to FREE tier.
        """
        # TODO: Integrate with actual billing system
        # For demo purposes, return FREE tier
        return PricingTier.FREE

    async def get_usage_metrics(self, shop_id: str) -> Optional[UsageMetrics]:
        """
        Get current usage metrics for a shop.

        Returns None if Redis unavailable or no metrics found.
        """
        if not self.redis_client:
            return None

        try:
            usage_key = self._get_usage_key(shop_id)
            data = self.redis_client.get(usage_key)

            if data:
                metrics_dict = json.loads(data)
                # Convert ISO timestamps back to datetime
                if metrics_dict.get('period_start'):
                    metrics_dict['period_start'] = datetime.fromisoformat(
                        metrics_dict['period_start']
                    )
                if metrics_dict.get('last_updated'):
                    metrics_dict['last_updated'] = datetime.fromisoformat(
                        metrics_dict['last_updated']
                    )
                return UsageMetrics(**metrics_dict)

            # Create new metrics if none exist
            return await self._initialize_metrics(shop_id)

        except Exception as e:
            logger.error(f"Failed to get usage metrics for shop {shop_id}: {e}")
            return None

    async def _initialize_metrics(self, shop_id: str) -> Optional[UsageMetrics]:
        """Initialize usage metrics for a new shop."""
        if not self.redis_client:
            return None

        try:
            tier = await self.get_shop_tier(shop_id)
            limits = TierLimits.get_limits(tier)

            now = datetime.utcnow()
            # Reset period on the 1st of each month
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            metrics = UsageMetrics(
                shop_id=shop_id,
                tier=tier,
                period_start=period_start,
                monthly_ai_requests_limit=limits.monthly_ai_requests,
                monthly_tokens_limit=limits.monthly_tokens,
                monthly_outfits_limit=limits.monthly_outfits,
                concurrent_requests_limit=limits.concurrent_requests,
            )

            # Store in Redis
            usage_key = self._get_usage_key(shop_id)
            self.redis_client.set(
                usage_key,
                json.dumps(asdict(metrics)),
                ex=90 * 24 * 60 * 60,  # Keep for 90 days
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to initialize metrics for shop {shop_id}: {e}")
            return None

    async def check_plan_limits(self, shop_id: str) -> Dict[str, Any]:
        """
        Check if shop is approaching or has exceeded plan limits.

        Returns upgrade recommendation and current usage status.
        """
        metrics = await self.get_usage_metrics(shop_id)

        if not metrics:
            return {
                "shop_id": shop_id,
                "upgrade_required": False,
                "error": "Unable to retrieve usage metrics",
            }

        exceeded = metrics.has_exceeded_limit()
        near_limit = metrics.is_near_limit(80.0)

        result = {
            "shop_id": shop_id,
            "current_tier": metrics.tier.value,
            "upgrade_required": exceeded,
            "near_limit": near_limit,
            "usage": {
                "ai_requests": {
                    "used": metrics.ai_requests,
                    "limit": metrics.monthly_ai_requests_limit,
                    "percentage": round(metrics.ai_requests_percentage, 1),
                },
                "tokens": {
                    "used": metrics.tokens_consumed,
                    "limit": metrics.monthly_tokens_limit,
                    "percentage": round(metrics.tokens_percentage, 1),
                },
                "outfits": {
                    "used": metrics.outfits_generated,
                    "limit": metrics.monthly_outfits_limit,
                    "percentage": round(metrics.outfits_percentage, 1),
                },
                "concurrent_requests": {
                    "active": metrics.active_requests,
                    "limit": metrics.concurrent_requests_limit,
                },
            },
            "period_start": metrics.period_start.isoformat(),
            "last_updated": metrics.last_updated.isoformat() if metrics.last_updated else None,
        }

        # Add upgrade recommendations
        if exceeded or near_limit:
            result["recommendations"] = self._get_upgrade_recommendations(metrics)

        return result

    def _get_upgrade_recommendations(self, metrics: UsageMetrics) -> List[str]:
        """Get upgrade recommendations based on usage patterns."""
        recommendations = []

        if metrics.ai_requests_percentage >= 90:
            recommendations.append("Upgrade to handle higher AI request volume")

        if metrics.tokens_percentage >= 90:
            recommendations.append("Upgrade for increased token allowance")

        if metrics.outfits_percentage >= 90:
            recommendations.append("Upgrade to generate more outfit recommendations")

        if not recommendations:
            recommendations.append("Consider upgrading to avoid service interruptions")

        return recommendations

    async def record_usage(
        self,
        shop_id: str,
        event_type: str,
        amount: int = 1,
        request_id: Optional[str] = None,
    ) -> bool:
        """
        Record usage event.

        Returns True if successfully recorded, False otherwise.
        """
        if not self.redis_client:
            logger.debug("Redis unavailable, skipping usage recording")
            return False

        try:
            # Get current metrics
            metrics = await self.get_usage_metrics(shop_id)
            if not metrics:
                return False

            # Update metrics based on event type
            if event_type == "ai_request":
                metrics.ai_requests += amount
            elif event_type == "token_usage":
                metrics.tokens_consumed += amount
            elif event_type == "outfit_generated":
                metrics.outfits_generated += amount
            elif event_type == "request_start":
                metrics.active_requests += 1
            elif event_type == "request_end":
                metrics.active_requests = max(0, metrics.active_requests - 1)

            metrics.last_updated = datetime.utcnow()

            # Store updated metrics
            usage_key = self._get_usage_key(shop_id)
            self.redis_client.set(
                usage_key,
                json.dumps(asdict(metrics)),
                ex=90 * 24 * 60 * 60,
            )

            # Record event for audit trail
            await self._record_event(shop_id, event_type, amount, request_id)

            logger.debug(f"Recorded usage: {event_type}={amount} for shop {shop_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to record usage for shop {shop_id}: {e}")
            return False

    async def _record_event(
        self,
        shop_id: str,
        event_type: str,
        amount: int,
        request_id: Optional[str],
    ) -> None:
        """Record usage event for audit trail."""
        if not self.redis_client:
            return

        try:
            event = UsageEvent(
                shop_id=shop_id,
                event_type=event_type,
                amount=amount,
                request_id=request_id,
            )

            events_key = self._get_events_key(shop_id, event.timestamp)
            event_data = asdict(event)
            event_data['timestamp'] = event.timestamp.isoformat()

            # Add to sorted set
            score = event.timestamp.timestamp()
            self.redis_client.zadd(
                events_key,
                {json.dumps(event_data): score}
            )

            # Set TTL (keep events for 30 days)
            self.redis_client.expire(events_key, 30 * 24 * 60 * 60)

        except Exception as e:
            logger.error(f"Failed to record usage event: {e}")

    async def can_make_ai_request(self, shop_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if shop can make an AI request.

        Returns (allowed, reason_if_denied)
        """
        metrics = await self.get_usage_metrics(shop_id)

        if not metrics:
            # Allow request if we can't check (fail open)
            return True, None

        if not metrics.can_make_request():
            if metrics.has_exceeded_limit():
                return False, "Monthly usage limit exceeded. Please upgrade your plan."
            elif metrics.active_requests >= metrics.concurrent_requests_limit:
                return False, "Too many concurrent requests. Please try again later."

        return True, None

    async def get_usage_warnings(self, shop_id: str) -> List[str]:
        """
        Get usage warnings for a shop.

        Returns list of warning messages if approaching limits.
        """
        metrics = await self.get_usage_metrics(shop_id)

        if not metrics:
            return []

        warnings = []

        if metrics.ai_requests_percentage >= 80:
            remaining = metrics.monthly_ai_requests_limit - metrics.ai_requests
            warnings.append(
                f"AI requests: {remaining} remaining this month "
                f"({metrics.ai_requests_percentage:.1f}% used)"
            )

        if metrics.tokens_percentage >= 80:
            remaining = metrics.monthly_tokens_limit - metrics.tokens_consumed
            warnings.append(
                f"Tokens: {remaining:,} remaining this month "
                f"({metrics.tokens_percentage:.1f}% used)"
            )

        if metrics.outfits_percentage >= 80:
            remaining = metrics.monthly_outfits_limit - metrics.outfits_generated
            warnings.append(
                f"Outfits: {remaining} remaining this month "
                f"({metrics.outfits_percentage:.1f}% used)"
            )

        return warnings


# Global instance for easy import
ai_metering = AIMeteringService()


# Helper functions for easy integration
async def check_usage_limits(shop_id: str) -> Dict[str, Any]:
    """Check plan limits for a shop."""
    return await ai_metering.check_plan_limits(shop_id)


async def record_ai_request(shop_id: str, request_id: Optional[str] = None) -> bool:
    """Record an AI request."""
    return await ai_metering.record_usage(shop_id, "ai_request", 1, request_id)


async def record_token_usage(shop_id: str, tokens: int, request_id: Optional[str] = None) -> bool:
    """Record token consumption."""
    return await ai_metering.record_usage(shop_id, "token_usage", tokens, request_id)


async def record_outfit_generated(shop_id: str, request_id: Optional[str] = None) -> bool:
    """Record outfit generation."""
    return await ai_metering.record_usage(shop_id, "outfit_generated", 1, request_id)


async def start_concurrent_request(shop_id: str, request_id: Optional[str] = None) -> bool:
    """Mark start of concurrent request."""
    return await ai_metering.record_usage(shop_id, "request_start", 1, request_id)


async def end_concurrent_request(shop_id: str, request_id: Optional[str] = None) -> bool:
    """Mark end of concurrent request."""
    return await ai_metering.record_usage(shop_id, "request_end", 1, request_id)
