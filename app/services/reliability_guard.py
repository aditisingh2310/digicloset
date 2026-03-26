"""
Self-Healing & Reliability Guards for Shopify multi-tenant FastAPI.

Provides fallback mechanisms, retry logic, and graceful degradation
when AI services are unavailable or slow.

Features:
- Exponential backoff retry
- Fallback recommendation modes
- Circuit breaker pattern
- Degraded mode logging
- Async-compatible timeouts
- Service health monitoring
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Callable, Any, Optional, Dict, List, TypeVar, Awaitable
from functools import wraps
from dataclasses import dataclass
from enum import Enum
import random
import os
try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None

from app.core.redis_runtime import log_optional_redis_issue, redis_connection_kwargs

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class DegradationLevel(str, Enum):
    """Levels of service degradation."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker."""
    service_name: str
    state: ServiceState = ServiceState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None

    # Configuration
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    expected_exception: tuple = (Exception,)

    def should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if self.state != ServiceState.OPEN:
            return False

        if not self.next_attempt_time:
            return True

        return datetime.utcnow() >= self.next_attempt_time

    def record_success(self) -> None:
        """Record a successful operation."""
        self.failure_count = 0
        self.last_success_time = datetime.utcnow()
        self.state = ServiceState.CLOSED
        self.next_attempt_time = None

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = ServiceState.OPEN
            self.next_attempt_time = datetime.utcnow() + timedelta(
                seconds=self.recovery_timeout_seconds
            )
        else:
            self.state = ServiceState.HALF_OPEN


@dataclass
class ServiceHealth:
    """Health status of a service."""
    service_name: str
    degradation_level: DegradationLevel = DegradationLevel.NORMAL
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    average_response_time: float = 0.0
    error_rate: float = 0.0

    def update_health(self, success: bool, response_time: float = 0.0) -> None:
        """Update health metrics."""
        self.last_check = datetime.utcnow()
        self.total_requests += 1

        if success:
            self.successful_requests += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

        # Update moving average response time
        if self.average_response_time == 0:
            self.average_response_time = response_time
        else:
            self.average_response_time = (
                self.average_response_time * 0.9 + response_time * 0.1
            )

        # Calculate error rate
        if self.total_requests > 0:
            self.error_rate = (
                (self.total_requests - self.successful_requests) / self.total_requests
            ) * 100

        # Determine degradation level
        self._update_degradation_level()

    def _update_degradation_level(self) -> None:
        """Update degradation level based on health metrics."""
        if self.consecutive_failures >= 10:
            self.degradation_level = DegradationLevel.UNAVAILABLE
        elif self.consecutive_failures >= 5:
            self.degradation_level = DegradationLevel.FALLBACK
        elif self.error_rate > 50 or self.average_response_time > 30:
            self.degradation_level = DegradationLevel.DEGRADED
        else:
            self.degradation_level = DegradationLevel.NORMAL


class ReliabilityGuard:
    """
    Self-healing reliability guard with circuit breakers and fallbacks.

    Provides retry logic, fallback modes, and graceful degradation.
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
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.service_health: Dict[str, ServiceHealth] = {}

        if not self.redis_client:
            if redis is None:
                log_optional_redis_issue(logger, "Redis package not available. Reliability features limited.")
                self.redis_client = None
                return
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    **redis_connection_kwargs(),
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Reliability guard initialized successfully")
            except Exception as e:
                log_optional_redis_issue(logger, f"Failed to connect to Redis: {e}. Reliability features limited.")
                self.redis_client = None

    def _get_circuit_key(self, service_name: str) -> str:
        """Generate Redis key for circuit breaker state."""
        return f"circuit:{service_name}"

    def _get_health_key(self, service_name: str) -> str:
        """Generate Redis key for service health."""
        return f"health:{service_name}"

    async def get_circuit_state(self, service_name: str) -> CircuitBreakerState:
        """Get circuit breaker state for a service."""
        if service_name in self.circuit_breakers:
            return self.circuit_breakers[service_name]

        if not self.redis_client:
            # Create default state
            state = CircuitBreakerState(service_name=service_name)
            self.circuit_breakers[service_name] = state
            return state

        try:
            key = self._get_circuit_key(service_name)
            data = self.redis_client.get(key)

            if data:
                import json
                state_dict = json.loads(data)
                # Convert ISO timestamps
                for field in ['last_failure_time', 'last_success_time', 'next_attempt_time']:
                    if state_dict.get(field):
                        state_dict[field] = datetime.fromisoformat(state_dict[field])
                state = CircuitBreakerState(**state_dict)
            else:
                state = CircuitBreakerState(service_name=service_name)

            self.circuit_breakers[service_name] = state
            return state

        except Exception as e:
            logger.error(f"Failed to get circuit state for {service_name}: {e}")
            state = CircuitBreakerState(service_name=service_name)
            self.circuit_breakers[service_name] = state
            return state

    async def _save_circuit_state(self, state: CircuitBreakerState) -> None:
        """Save circuit breaker state to Redis."""
        if not self.redis_client:
            return

        try:
            key = self._get_circuit_key(state.service_name)
            import json
            state_dict = {
                k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in state.__dict__.items()
            }
            self.redis_client.set(
                key,
                json.dumps(state_dict),
                ex=24 * 60 * 60,  # Keep for 24 hours
            )
        except Exception as e:
            logger.error(f"Failed to save circuit state: {e}")

    async def get_service_health(self, service_name: str) -> ServiceHealth:
        """Get health status for a service."""
        if service_name in self.service_health:
            return self.service_health[service_name]

        if not self.redis_client:
            health = ServiceHealth(service_name=service_name)
            self.service_health[service_name] = health
            return health

        try:
            key = self._get_health_key(service_name)
            data = self.redis_client.get(key)

            if data:
                import json
                health_dict = json.loads(data)
                if health_dict.get('last_check'):
                    health_dict['last_check'] = datetime.fromisoformat(health_dict['last_check'])
                health = ServiceHealth(**health_dict)
            else:
                health = ServiceHealth(service_name=service_name)

            self.service_health[service_name] = health
            return health

        except Exception as e:
            logger.error(f"Failed to get service health for {service_name}: {e}")
            health = ServiceHealth(service_name=service_name)
            self.service_health[service_name] = health
            return health

    async def _save_service_health(self, health: ServiceHealth) -> None:
        """Save service health to Redis."""
        if not self.redis_client:
            return

        try:
            key = self._get_health_key(health.service_name)
            import json
            health_dict = {
                k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in health.__dict__.items()
            }
            self.redis_client.set(
                key,
                json.dumps(health_dict),
                ex=24 * 60 * 60,  # Keep for 24 hours
            )
        except Exception as e:
            logger.error(f"Failed to save service health: {e}")

    async def execute_with_circuit_breaker(
        self,
        service_name: str,
        func: Callable[..., Awaitable[T]],
        *args,
        fallback_func: Optional[Callable[..., Awaitable[T]]] = None,
        **kwargs
    ) -> T:
        """
        Execute function with circuit breaker protection.

        If circuit is open, calls fallback_func if provided.
        """
        state = await self.get_circuit_state(service_name)

        # Check if circuit is open
        if state.state == ServiceState.OPEN and not state.should_attempt_reset():
            if fallback_func:
                logger.warning(f"Circuit open for {service_name}, using fallback")
                return await fallback_func(*args, **kwargs)
            else:
                raise Exception(f"Service {service_name} is currently unavailable")

        # Execute function
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            response_time = time.time() - start_time

            # Record success
            state.record_success()
            await self._save_circuit_state(state)

            # Update health
            health = await self.get_service_health(service_name)
            health.update_health(success=True, response_time=response_time)
            await self._save_service_health(health)

            return result

        except Exception as e:
            response_time = time.time() - start_time

            # Record failure
            state.record_failure()
            await self._save_circuit_state(state)

            # Update health
            health = await self.get_service_health(service_name)
            health.update_health(success=False, response_time=response_time)
            await self._save_service_health(health)

            # Try fallback if circuit allows
            if fallback_func and state.state != ServiceState.OPEN:
                logger.warning(f"Service {service_name} failed, using fallback: {e}")
                return await fallback_func(*args, **kwargs)

            raise

    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        **kwargs
    ) -> T:
        """
        Execute function with exponential backoff retry.

        Args:
            func: Async function to execute
            max_attempts: Maximum number of attempts
            base_delay: Initial delay between attempts
            max_delay: Maximum delay between attempts
            backoff_factor: Exponential backoff multiplier
            jitter: Add random jitter to delay
        """
        last_exception = None

        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt == max_attempts - 1:
                    # Last attempt failed
                    logger.error(
                        f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                    )
                    raise e

                # Calculate delay
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)

                if jitter:
                    # Add random jitter (±25%)
                    jitter_amount = delay * 0.25
                    delay += random.uniform(-jitter_amount, jitter_amount)

                logger.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f}s"
                )

                await asyncio.sleep(delay)

        # This should never be reached, but just in case
        raise last_exception

    def circuit_breaker(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        expected_exception: tuple = (Exception,),
    ):
        """
        Decorator for circuit breaker protection.

        Usage:
            @reliability_guard.circuit_breaker("ai_service")
            async def call_ai_service():
                ...
        """
        def decorator(func: Callable[..., Awaitable[T]]):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                state = await self.get_circuit_state(service_name)

                # Update state configuration
                state.failure_threshold = failure_threshold
                state.recovery_timeout_seconds = recovery_timeout_seconds
                state.expected_exception = expected_exception

                return await self.execute_with_circuit_breaker(
                    service_name, func, *args, **kwargs
                )

            return wrapper

        return decorator

    def with_retry(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        """
        Decorator for retry with exponential backoff.

        Usage:
            @reliability_guard.with_retry(max_attempts=5)
            async def unreliable_operation():
                ...
        """
        def decorator(func: Callable[..., Awaitable[T]]):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await self.execute_with_retry(
                    func, *args,
                    max_attempts=max_attempts,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    backoff_factor=backoff_factor,
                    jitter=jitter,
                    **kwargs
                )

            return wrapper

        return decorator


# Fallback recommendation functions
async def fallback_outfit_recommendations(
    shop_id: str,
    product_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Fallback outfit recommendations when AI service is unavailable.

    Returns basic recommendations based on product category patterns.
    """
    logger.info(f"Using fallback recommendations for shop {shop_id}, product {product_id}")

    # Simple fallback: return generic outfit suggestions
    # In production, this could use cached recommendations or rules-based logic
    return [
        {
            "id": f"fallback_{i}",
            "name": f"Basic Outfit {i}",
            "description": "Fallback recommendation due to service degradation",
            "confidence": 0.5,
            "products": [
                {
                    "id": product_id,
                    "name": "Featured Product",
                    "category": "unknown",
                }
            ],
            "degraded_mode": True,
        }
        for i in range(min(limit, 3))
    ]


async def fallback_ai_analysis(
    image_data: bytes,
    text: str = "",
) -> Dict[str, Any]:
    """
    Fallback AI analysis when AI service is unavailable.

    Returns basic analysis without ML processing.
    """
    logger.info("Using fallback AI analysis due to service degradation")

    return {
        "colors": ["#808080"],  # Gray as fallback
        "dominant_color": "#808080",
        "fitScore": 0.5,
        "recommendations": [
            "Service temporarily unavailable - showing basic analysis",
            "Please try again later for full AI-powered recommendations"
        ],
        "method": "fallback",
        "degraded_mode": True,
    }


# Global instance
reliability_guard = ReliabilityGuard()


# Helper decorators for common use cases
def ai_service_circuit_breaker(fallback_func=None):
    """Circuit breaker for AI service calls."""
    return reliability_guard.circuit_breaker(
        "ai_service",
        failure_threshold=3,
        recovery_timeout_seconds=30,
    )


def ai_retry():
    """Retry decorator for AI operations."""
    return reliability_guard.with_retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
    )


# Middleware for tracking degraded mode
class DegradationTrackingMiddleware:
    """
    Middleware to track and log when services enter degraded mode.

    Usage:
        app.add_middleware(DegradationTrackingMiddleware)
    """

    def __init__(self, app):
        self.app = app
        self.last_logged = {}  # service -> last log time

    async def __call__(self, request, call_next):
        # Check service health before processing
        services_to_check = ["ai_service", "redis_cache", "external_api"]

        for service_name in services_to_check:
            health = await reliability_guard.get_service_health(service_name)

            if health.degradation_level != DegradationLevel.NORMAL:
                # Only log once per hour per service
                last_log = self.last_logged.get(service_name)
                if not last_log or (datetime.utcnow() - last_log).seconds > 3600:
                    logger.warning(
                        f"Service {service_name} in {health.degradation_level.value} mode",
                        extra={
                            "service": service_name,
                            "degradation_level": health.degradation_level.value,
                            "error_rate": round(health.error_rate, 2),
                            "avg_response_time": round(health.average_response_time, 2),
                            "consecutive_failures": health.consecutive_failures,
                        }
                    )
                    self.last_logged[service_name] = datetime.utcnow()

        response = await call_next(request)
        return response
