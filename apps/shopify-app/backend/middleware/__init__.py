"""Production-grade FastAPI middleware modules."""

from .rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitMiddleware,
    rate_limit,
)
from .tenant_isolation import (
    TenantContext,
    TenantGuardError,
    extract_shop_id,
    get_shop_id,
    require_tenant,
    TenantMiddleware,
    TenantAwareDB,
    TenantAwareCache,
)

__all__ = [
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitMiddleware",
    "rate_limit",
    "TenantContext",
    "TenantGuardError",
    "extract_shop_id",
    "get_shop_id",
    "require_tenant",
    "TenantMiddleware",
    "TenantAwareDB",
    "TenantAwareCache",
]
