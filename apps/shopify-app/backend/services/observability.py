"""
Observability Service for Shopify multi-tenant FastAPI.

Provides structured event logging for business metrics and system observability.
Tracks outfit performance, user interactions, and system events safely.

Features:
- Structured event logging
- PII-safe data handling
- Event correlation with request_id
- Async-compatible event processing
- Event aggregation and metrics
- Integration with existing logging infrastructure
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import os
try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of business events to track."""
    # Outfit events
    OUTFIT_GENERATED = "outfit_generated"
    OUTFIT_VIEWED = "outfit_viewed"
    OUTFIT_CLICKED = "outfit_clicked"
    OUTFIT_SHARED = "outfit_shared"
    OUTFIT_SAVED = "outfit_saved"

    # Product events
    PRODUCT_VIEWED = "product_viewed"
    PRODUCT_ADDED_TO_CART = "product_added_to_cart"
    PRODUCT_PURCHASED = "product_purchased"

    # User interaction events
    PAGE_VIEW = "page_view"
    SEARCH_PERFORMED = "search_performed"
    FILTER_APPLIED = "filter_applied"

    # System events
    API_REQUEST = "api_request"
    API_ERROR = "api_error"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Business events
    REVENUE_ATTRIBUTED = "revenue_attributed"
    USAGE_LIMIT_APPROACHED = "usage_limit_approached"
    PLAN_UPGRADED = "plan_upgraded"


@dataclass
class BusinessEvent:
    """Structured business event."""
    event_type: EventType
    shop_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    # Event-specific data
    event_data: Dict[str, Any] = None

    # Metadata
    timestamp: Optional[datetime] = None
    source: str = "api"  # api, widget, webhook, etc.
    version: str = "1.0"

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.event_data is None:
            self.event_data = {}
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())


class ObservabilityService:
    """
    Redis-backed observability service for structured event logging.

    Provides event tracking, aggregation, and metrics for business intelligence.
    """

    def __init__(
        self,
        redis_url: str = None,
        redis_client: Any = None,
        enable_structured_logging: bool = True,
    ):
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
        self.redis_client = redis_client
        self.enable_structured_logging = enable_structured_logging

        if not self.redis_client:
            if redis is None:
                logger.warning("Redis package not available. Observability disabled.")
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
                logger.info("Observability service initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Observability disabled.")
                self.redis_client = None

    def _get_event_key(self, shop_id: str, event_type: str, date: datetime) -> str:
        """Generate Redis key for events."""
        date_str = date.strftime("%Y-%m-%d")
        return f"events:{shop_id}:{event_type}:{date_str}"

    def _get_metrics_key(self, shop_id: str, metric_name: str) -> str:
        """Generate Redis key for aggregated metrics."""
        return f"metrics:{shop_id}:{metric_name}"

    async def log_event(self, event: BusinessEvent) -> bool:
        """
        Log a business event.

        Returns True if successfully logged, False otherwise.
        """
        # Always log to structured logger first
        if self.enable_structured_logging:
            self._log_structured_event(event)

        if not self.redis_client:
            return True  # Still consider successful if structured logging worked

        try:
            # Store event in daily bucket
            event_key = self._get_event_key(
                event.shop_id,
                event.event_type.value,
                event.timestamp
            )

            event_data = asdict(event)
            event_data['timestamp'] = event.timestamp.isoformat()
            event_data['event_type'] = event.event_type.value  # Convert enum to string

            # Add to sorted set with timestamp as score
            score = event.timestamp.timestamp()
            self.redis_client.zadd(
                event_key,
                {json.dumps(event_data): score}
            )

            # Set TTL for event bucket (keep for 90 days)
            self.redis_client.expire(event_key, 90 * 24 * 60 * 60)

            # Update real-time metrics
            await self._update_realtime_metrics(event)

            return True

        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return False

    def _log_structured_event(self, event: BusinessEvent) -> None:
        """Log event to structured logger."""
        try:
            log_data = {
                "event_type": event.event_type.value,
                "shop_id": event.shop_id,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
                "version": event.version,
            }

            # Add optional fields
            if event.user_id:
                log_data["user_id"] = event.user_id
            if event.session_id:
                log_data["session_id"] = event.session_id
            if event.request_id:
                log_data["request_id"] = event.request_id

            # Add event-specific data (PII-safe)
            for key, value in event.event_data.items():
                if isinstance(value, (str, int, float, bool)):
                    log_data[f"event_{key}"] = str(value)
                elif isinstance(value, list):
                    log_data[f"event_{key}"] = [str(v) for v in value if isinstance(v, (str, int, float, bool))]

            logger.info(
                f"Business event: {event.event_type.value}",
                extra=log_data
            )

        except Exception as e:
            logger.error(f"Failed to log structured event: {e}")

    async def _update_realtime_metrics(self, event: BusinessEvent) -> None:
        """Update real-time aggregated metrics."""
        if not self.redis_client:
            return

        try:
            # Update event count metrics
            count_key = self._get_metrics_key(event.shop_id, "event_counts")
            current_counts = self.redis_client.get(count_key)

            if current_counts:
                counts = json.loads(current_counts)
            else:
                counts = {}

            event_type = event.event_type.value
            counts[event_type] = counts.get(event_type, 0) + 1

            self.redis_client.set(
                count_key,
                json.dumps(counts),
                ex=7 * 24 * 60 * 60,  # Keep for 7 days
            )

            # Update outfit-specific metrics if applicable
            if "outfit" in event.event_data:
                outfit_id = event.event_data.get("outfit_id")
                if outfit_id:
                    outfit_key = self._get_metrics_key(event.shop_id, f"outfit_{outfit_id}")
                    current_outfit = self.redis_client.get(outfit_key)

                    if current_outfit:
                        outfit_data = json.loads(current_outfit)
                    else:
                        outfit_data = {
                            "outfit_id": outfit_id,
                            "created_at": event.timestamp.isoformat(),
                            "events": {},
                        }

                    event_type = event.event_type.value
                    outfit_data["events"][event_type] = outfit_data["events"].get(event_type, 0) + 1
                    outfit_data["last_updated"] = event.timestamp.isoformat()

                    self.redis_client.set(
                        outfit_key,
                        json.dumps(outfit_data),
                        ex=90 * 24 * 60 * 60,  # Keep for 90 days
                    )

        except Exception as e:
            logger.error(f"Failed to update realtime metrics: {e}")

    async def get_event_counts(
        self,
        shop_id: str,
        event_types: Optional[List[str]] = None,
        days: int = 7,
    ) -> Dict[str, int]:
        """
        Get event counts for a shop over the last N days.

        Args:
            shop_id: Shop identifier
            event_types: List of event types to count (None for all)
            days: Number of days to look back

        Returns:
            Dict of event_type -> count
        """
        if not self.redis_client:
            return {}

        try:
            counts = {}

            # Check each day
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=i)

                if event_types:
                    # Count specific event types
                    for event_type in event_types:
                        key = self._get_event_key(shop_id, event_type, date)
                        count = self.redis_client.zcount(key, '-inf', '+inf')
                        counts[event_type] = counts.get(event_type, 0) + count
                else:
                    # Count all event types for this shop/date
                    pattern = f"events:{shop_id}:*:{date.strftime('%Y-%m-%d')}"
                    keys = self.redis_client.keys(pattern)

                    for key in keys:
                        # Extract event type from key
                        parts = key.split(":")
                        if len(parts) >= 3:
                            event_type = parts[2]
                            count = self.redis_client.zcount(key, '-inf', '+inf')
                            counts[event_type] = counts.get(event_type, 0) + count

            return counts

        except Exception as e:
            logger.error(f"Failed to get event counts for shop {shop_id}: {e}")
            return {}

    async def get_outfit_performance(
        self,
        shop_id: str,
        outfit_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics for outfits.

        Args:
            shop_id: Shop identifier
            outfit_id: Specific outfit ID (None for all)
            limit: Maximum number of outfits to return

        Returns:
            List of outfit performance data
        """
        if not self.redis_client:
            return []

        try:
            if outfit_id:
                # Get specific outfit
                outfit_key = self._get_metrics_key(shop_id, f"outfit_{outfit_id}")
                data = self.redis_client.get(outfit_key)

                if data:
                    return [json.loads(data)]
                return []

            # Get all outfit keys for this shop
            pattern = f"metrics:{shop_id}:outfit_*"
            outfit_keys = self.redis_client.keys(pattern)

            outfits = []
            for key in outfit_keys:
                data = self.redis_client.get(key)
                if data:
                    outfit_data = json.loads(data)
                    outfits.append(outfit_data)

            # Sort by total events (descending)
            outfits.sort(
                key=lambda x: sum(x.get("events", {}).values()),
                reverse=True
            )

            return outfits[:limit]

        except Exception as e:
            logger.error(f"Failed to get outfit performance for shop {shop_id}: {e}")
            return []

    async def get_user_journey(
        self,
        shop_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Get user journey events for analysis.

        Args:
            shop_id: Shop identifier
            user_id: User identifier
            session_id: Session identifier (optional)
            hours: Hours to look back

        Returns:
            List of user events in chronological order
        """
        if not self.redis_client:
            return []

        try:
            events = []
            start_time = datetime.utcnow() - timedelta(hours=hours)
            start_score = start_time.timestamp()

            # Get all event types for this shop
            pattern = f"events:{shop_id}:*"
            event_keys = self.redis_client.keys(pattern)

            for key in event_keys:
                # Get events after start time
                event_list = self.redis_client.zrangebyscore(
                    key, start_score, '+inf', withscores=True
                )

                for event_json, score in event_list:
                    event_data = json.loads(event_json)

                    # Filter by user_id
                    if event_data.get("user_id") == user_id:
                        # Filter by session_id if provided
                        if not session_id or event_data.get("session_id") == session_id:
                            events.append(event_data)

            # Sort by timestamp
            events.sort(key=lambda x: x.get("timestamp", ""))

            return events

        except Exception as e:
            logger.error(f"Failed to get user journey for shop {shop_id}, user {user_id}: {e}")
            return []


# Global instance
observability = ObservabilityService()


# Helper functions for easy event logging
async def log_outfit_generated(
    shop_id: str,
    outfit_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **event_data
) -> bool:
    """Log outfit generation event."""
    event = BusinessEvent(
        event_type=EventType.OUTFIT_GENERATED,
        shop_id=shop_id,
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        event_data={
            "outfit_id": outfit_id,
            **event_data
        }
    )
    return await observability.log_event(event)


async def log_outfit_clicked(
    shop_id: str,
    outfit_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **event_data
) -> bool:
    """Log outfit click event."""
    event = BusinessEvent(
        event_type=EventType.OUTFIT_CLICKED,
        shop_id=shop_id,
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        event_data={
            "outfit_id": outfit_id,
            **event_data
        }
    )
    return await observability.log_event(event)


async def log_product_purchased(
    shop_id: str,
    product_id: str,
    order_id: str,
    revenue: float,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **event_data
) -> bool:
    """Log product purchase event."""
    event = BusinessEvent(
        event_type=EventType.PRODUCT_PURCHASED,
        shop_id=shop_id,
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        event_data={
            "product_id": product_id,
            "order_id": order_id,
            "revenue": revenue,
            **event_data
        }
    )
    return await observability.log_event(event)


async def log_api_request(
    shop_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time: float,
    request_id: Optional[str] = None,
    **event_data
) -> bool:
    """Log API request event."""
    event = BusinessEvent(
        event_type=EventType.API_REQUEST,
        shop_id=shop_id,
        request_id=request_id,
        event_data={
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time": response_time,
            **event_data
        }
    )
    return await observability.log_event(event)


async def log_revenue_attributed(
    shop_id: str,
    outfit_id: str,
    order_id: str,
    revenue: float,
    attribution_window_days: int,
    request_id: Optional[str] = None,
    **event_data
) -> bool:
    """Log revenue attribution event."""
    event = BusinessEvent(
        event_type=EventType.REVENUE_ATTRIBUTED,
        shop_id=shop_id,
        request_id=request_id,
        event_data={
            "outfit_id": outfit_id,
            "order_id": order_id,
            "revenue": revenue,
            "attribution_window_days": attribution_window_days,
            **event_data
        }
    )
    return await observability.log_event(event)
