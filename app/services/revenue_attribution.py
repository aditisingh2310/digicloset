"""
Revenue Attribution Engine for Shopify multi-tenant FastAPI.

Tracks outfit impressions, clicks, add-to-cart events, and completed orders
to calculate revenue influenced by outfit recommendations.

Features:
- Tenant-scoped metrics storage
- Event tracking with attribution
- Revenue calculation with lookback windows
- Async-compatible with Redis backend
- Graceful degradation on Redis failure
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import os

try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None

logger = logging.getLogger(__name__)


class AttributionEventType(str, Enum):
    """Types of attribution events."""
    OUTFIT_IMPRESSION = "outfit_impression"
    OUTFIT_CLICK = "outfit_click"
    ADD_TO_CART = "add_to_cart"
    ORDER_COMPLETED = "order_completed"


@dataclass
class AttributionEvent:
    """Represents an attribution event."""
    event_type: AttributionEventType
    shop_id: str
    outfit_id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    order_id: Optional[str] = None
    revenue: Optional[float] = None
    timestamp: Optional[datetime] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class RevenueMetrics:
    """Revenue attribution metrics for a shop."""
    shop_id: str
    total_impressions: int = 0
    total_clicks: int = 0
    total_add_to_cart: int = 0
    total_orders: int = 0
    total_revenue_influenced: float = 0.0
    average_order_value: float = 0.0
    conversion_rate: float = 0.0
    click_through_rate: float = 0.0
    last_updated: Optional[datetime] = None

    @property
    def revenue_per_impression(self) -> float:
        """Calculate revenue per impression."""
        return self.total_revenue_influenced / max(self.total_impressions, 1)

    @property
    def revenue_per_click(self) -> float:
        """Calculate revenue per click."""
        return self.total_revenue_influenced / max(self.total_clicks, 1)


class RevenueAttributionEngine:
    """
    Redis-backed revenue attribution engine.

    Tracks outfit performance and calculates revenue influence
    with configurable attribution windows.
    """

    def __init__(
        self,
        redis_url: str = None,
        attribution_window_days: int = 30,
        redis_client: Any = None,
    ):
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
        self.attribution_window_days = attribution_window_days
        self.redis_client = redis_client

        if not self.redis_client:
            if redis is None:
                logger.warning("Redis package not available. Attribution disabled.")
                self.redis_client = None
                return
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=10,
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Revenue attribution engine initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Attribution disabled.")
                self.redis_client = None

    def _get_event_key(self, shop_id: str, event_type: str, date: datetime) -> str:
        """Generate Redis key for events."""
        date_str = date.strftime("%Y-%m-%d")
        return f"attribution:{shop_id}:{event_type}:{date_str}"

    def _get_metrics_key(self, shop_id: str) -> str:
        """Generate Redis key for aggregated metrics."""
        return f"metrics:{shop_id}"

    def _get_outfit_key(self, shop_id: str, outfit_id: str) -> str:
        """Generate Redis key for outfit-specific metrics."""
        return f"outfit:{shop_id}:{outfit_id}"

    async def track_event(self, event: AttributionEvent) -> bool:
        """
        Track an attribution event.

        Returns True if successfully tracked, False otherwise.
        """
        if not self.redis_client:
            logger.debug("Redis unavailable, skipping event tracking")
            return False

        try:
            # Store event in daily bucket
            event_key = self._get_event_key(
                event.shop_id,
                event.event_type.value,
                event.timestamp
            )

            event_data = asdict(event)
            event_data['timestamp'] = event.timestamp.isoformat()

            # Add to sorted set with timestamp as score
            score = event.timestamp.timestamp()
            self.redis_client.zadd(
                event_key,
                {json.dumps(event_data): score}
            )

            # Set TTL for event bucket (keep for attribution window + buffer)
            ttl_days = self.attribution_window_days + 7
            self.redis_client.expire(event_key, ttl_days * 24 * 60 * 60)

            # Update aggregated metrics
            await self._update_metrics(event)

            # Update outfit-specific metrics
            await self._update_outfit_metrics(event)

            logger.debug(f"Tracked event: {event.event_type} for shop {event.shop_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to track event: {e}")
            return False

    async def _update_metrics(self, event: AttributionEvent) -> None:
        """Update aggregated metrics for the shop."""
        if not self.redis_client:
            return

        try:
            metrics_key = self._get_metrics_key(event.shop_id)

            # Get current metrics
            current_data = self.redis_client.get(metrics_key)
            if current_data:
                metrics = RevenueMetrics(**json.loads(current_data))
            else:
                metrics = RevenueMetrics(shop_id=event.shop_id)

            # Update counters
            if event.event_type == AttributionEventType.OUTFIT_IMPRESSION:
                metrics.total_impressions += 1
            elif event.event_type == AttributionEventType.OUTFIT_CLICK:
                metrics.total_clicks += 1
            elif event.event_type == AttributionEventType.ADD_TO_CART:
                metrics.total_add_to_cart += 1
            elif event.event_type == AttributionEventType.ORDER_COMPLETED:
                metrics.total_orders += 1
                if event.revenue:
                    metrics.total_revenue_influenced += event.revenue

            # Recalculate derived metrics
            metrics.average_order_value = (
                metrics.total_revenue_influenced / max(metrics.total_orders, 1)
            )
            metrics.conversion_rate = (
                metrics.total_orders / max(metrics.total_impressions, 1)
            )
            metrics.click_through_rate = (
                metrics.total_clicks / max(metrics.total_impressions, 1)
            )
            metrics.last_updated = datetime.utcnow()

            # Store updated metrics
            self.redis_client.set(
                metrics_key,
                json.dumps(asdict(metrics)),
                ex=365 * 24 * 60 * 60  # Keep for 1 year
            )

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    async def _update_outfit_metrics(self, event: AttributionEvent) -> None:
        """Update outfit-specific metrics."""
        if not self.redis_client:
            return

        try:
            outfit_key = self._get_outfit_key(event.shop_id, event.outfit_id)

            # Get current outfit metrics
            current_data = self.redis_client.get(outfit_key)
            if current_data:
                outfit_metrics = json.loads(current_data)
            else:
                outfit_metrics = {
                    "shop_id": event.shop_id,
                    "outfit_id": event.outfit_id,
                    "impressions": 0,
                    "clicks": 0,
                    "add_to_cart": 0,
                    "orders": 0,
                    "revenue": 0.0,
                    "created_at": event.timestamp.isoformat(),
                    "last_updated": event.timestamp.isoformat(),
                }

            # Update counters
            if event.event_type == AttributionEventType.OUTFIT_IMPRESSION:
                outfit_metrics["impressions"] += 1
            elif event.event_type == AttributionEventType.OUTFIT_CLICK:
                outfit_metrics["clicks"] += 1
            elif event.event_type == AttributionEventType.ADD_TO_CART:
                outfit_metrics["add_to_cart"] += 1
            elif event.event_type == AttributionEventType.ORDER_COMPLETED:
                outfit_metrics["orders"] += 1
                if event.revenue:
                    outfit_metrics["revenue"] += event.revenue

            outfit_metrics["last_updated"] = datetime.utcnow().isoformat()

            # Store updated outfit metrics
            self.redis_client.set(
                outfit_key,
                json.dumps(outfit_metrics),
                ex=90 * 24 * 60 * 60  # Keep for 90 days
            )

        except Exception as e:
            logger.error(f"Failed to update outfit metrics: {e}")

    async def get_metrics(self, shop_id: str) -> Optional[RevenueMetrics]:
        """
        Get aggregated revenue metrics for a shop.

        Returns None if no metrics found or Redis unavailable.
        """
        if not self.redis_client:
            return None

        try:
            metrics_key = self._get_metrics_key(shop_id)
            data = self.redis_client.get(metrics_key)

            if data:
                metrics_dict = json.loads(data)
                # Convert ISO timestamp back to datetime
                if metrics_dict.get('last_updated'):
                    metrics_dict['last_updated'] = datetime.fromisoformat(
                        metrics_dict['last_updated']
                    )
                return RevenueMetrics(**metrics_dict)

        except Exception as e:
            logger.error(f"Failed to get metrics for shop {shop_id}: {e}")

        return None

    async def get_outfit_performance(
        self,
        shop_id: str,
        limit: int = 50,
        min_impressions: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get top-performing outfits for a shop.

        Returns list of outfit metrics sorted by revenue.
        """
        if not self.redis_client:
            return []

        try:
            # Get all outfit keys for this shop
            pattern = f"outfit:{shop_id}:*"
            outfit_keys = self.redis_client.keys(pattern)

            outfits = []
            for key in outfit_keys:
                data = self.redis_client.get(key)
                if data:
                    outfit_data = json.loads(data)
                    if outfit_data.get("impressions", 0) >= min_impressions:
                        outfits.append(outfit_data)

            # Sort by revenue descending
            outfits.sort(key=lambda x: x.get("revenue", 0), reverse=True)
            return outfits[:limit]

        except Exception as e:
            logger.error(f"Failed to get outfit performance for shop {shop_id}: {e}")
            return []

    async def calculate_revenue_influenced(
        self,
        shop_id: str,
        lookback_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Calculate total revenue influenced by outfits for a shop.

        Uses attribution window to determine which orders were influenced.
        """
        if not self.redis_client:
            return {
                "shop_id": shop_id,
                "total_revenue_influenced": 0.0,
                "orders_influenced": 0,
                "attribution_window_days": lookback_days,
                "error": "Redis unavailable",
            }

        try:
            # Get all order events within lookback window
            start_date = datetime.utcnow() - timedelta(days=lookback_days)
            total_revenue = 0.0
            total_orders = 0

            # Scan for order events
            pattern = f"attribution:{shop_id}:{AttributionEventType.ORDER_COMPLETED.value}:*"
            order_keys = self.redis_client.keys(pattern)

            for key in order_keys:
                # Check if key date is within lookback window
                try:
                    date_str = key.split(":")[-1]
                    event_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if event_date >= start_date.date():
                        # Get all events for this date
                        events = self.redis_client.zrange(key, 0, -1)
                        for event_json in events:
                            event_data = json.loads(event_json)
                            revenue = event_data.get("revenue", 0.0)
                            total_revenue += revenue
                            if revenue > 0:
                                total_orders += 1
                except (ValueError, IndexError):
                    continue

            return {
                "shop_id": shop_id,
                "total_revenue_influenced": total_revenue,
                "orders_influenced": total_orders,
                "attribution_window_days": lookback_days,
                "average_order_value": total_revenue / max(total_orders, 1),
                "calculated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to calculate revenue for shop {shop_id}: {e}")
            return {
                "shop_id": shop_id,
                "total_revenue_influenced": 0.0,
                "orders_influenced": 0,
                "attribution_window_days": lookback_days,
                "error": str(e),
            }

    async def get_aov_comparison(
        self,
        shop_id: str,
        lookback_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Compare AOV before vs after outfit implementation.

        This is a simplified implementation - in production you'd need
        historical order data from Shopify API.
        """
        # Get influenced orders
        influenced = await self.calculate_revenue_influenced(shop_id, lookback_days)

        # For now, return placeholder - would need Shopify API integration
        # to get actual AOV comparison
        return {
            "shop_id": shop_id,
            "aov_before_outfits": 0.0,  # Would need historical data
            "aov_after_outfits": influenced.get("average_order_value", 0.0),
            "conversion_lift_percentage": 0.0,  # Would need baseline data
            "lookback_days": lookback_days,
            "note": "AOV comparison requires Shopify API integration for historical data",
        }


# Global instance for easy import
revenue_engine = RevenueAttributionEngine()


# Helper functions for easy integration
async def track_outfit_impression(
    shop_id: str,
    outfit_id: str,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> bool:
    """Track outfit impression event."""
    event = AttributionEvent(
        event_type=AttributionEventType.OUTFIT_IMPRESSION,
        shop_id=shop_id,
        outfit_id=outfit_id,
        session_id=session_id,
        request_id=request_id,
    )
    return await revenue_engine.track_event(event)


async def track_outfit_click(
    shop_id: str,
    outfit_id: str,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> bool:
    """Track outfit click event."""
    event = AttributionEvent(
        event_type=AttributionEventType.OUTFIT_CLICK,
        shop_id=shop_id,
        outfit_id=outfit_id,
        session_id=session_id,
        request_id=request_id,
    )
    return await revenue_engine.track_event(event)


async def track_add_to_cart(
    shop_id: str,
    outfit_id: str,
    product_id: str,
    variant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> bool:
    """Track add-to-cart event influenced by outfit."""
    event = AttributionEvent(
        event_type=AttributionEventType.ADD_TO_CART,
        shop_id=shop_id,
        outfit_id=outfit_id,
        product_id=product_id,
        variant_id=variant_id,
        session_id=session_id,
        request_id=request_id,
    )
    return await revenue_engine.track_event(event)


async def track_order_completed(
    shop_id: str,
    outfit_id: str,
    order_id: str,
    revenue: float,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> bool:
    """Track completed order influenced by outfit."""
    event = AttributionEvent(
        event_type=AttributionEventType.ORDER_COMPLETED,
        shop_id=shop_id,
        outfit_id=outfit_id,
        order_id=order_id,
        revenue=revenue,
        session_id=session_id,
        request_id=request_id,
    )
    return await revenue_engine.track_event(event)

# Backwards-compatible singleton alias
revenue_attribution = revenue_engine
