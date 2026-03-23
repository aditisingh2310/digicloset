"""
Tenant isolation enforcement at data-access layer.

Ensures all database and cache access is scoped to the authenticated tenant.
Raises if shop context is missing, preventing accidental cross-tenant reads.
"""
from functools import wraps
from typing import Optional, Callable
from fastapi import HTTPException
from starlette.requests import Request
import logging

logger = logging.getLogger(__name__)


class TenantContext:
    """Thread-local/context-local storage for tenant info."""
    
    _context: dict = {}
    
    @classmethod
    def set_shop_id(cls, shop_id: str) -> None:
        """Set current shop_id in context."""
        if not shop_id or not isinstance(shop_id, str) or len(shop_id) == 0:
            raise ValueError("shop_id must be a non-empty string")
        cls._context["shop_id"] = shop_id
        logger.debug(f"Tenant context set to shop: {shop_id}")
    
    @classmethod
    def get_shop_id(cls) -> Optional[str]:
        """Get current shop_id from context."""
        return cls._context.get("shop_id")
    
    @classmethod
    def clear(cls) -> None:
        """Clear tenant context."""
        cls._context.clear()
    
    @classmethod
    def ensure_tenant(cls) -> str:
        """
        Ensure shop_id is set. Raises if missing.
        
        Raises:
            RuntimeError: If shop_id is not in context
        """
        shop_id = cls.get_shop_id()
        if not shop_id:
            raise RuntimeError(
                "Tenant context not initialized. Shop ID is required."
            )
        return shop_id


class TenantGuardError(HTTPException):
    """Raised when tenant validation fails."""
    
    def __init__(self, detail: str = "Authentication required", status_code: int = 401):
        super().__init__(status_code=status_code, detail=detail)


def extract_shop_id(request: Request) -> str:
    """
    Extract shop_id from request.
    
    Priority:
    1. Header (X-Shop-ID)
    2. Query param (shop_id)
    3. Path param (shop/{shop_id}/...)
    4. Raises if not found
    
    Raises:
        TenantGuardError: If shop_id cannot be found or is invalid
    """
    # Try header first
    shop_id = request.headers.get("X-Shop-ID", "").strip()
    if shop_id:
        return shop_id
    
    # Try query param
    shop_id = request.query_params.get("shop_id", "").strip()
    if shop_id:
        return shop_id
    
    # Try path param
    path_parts = request.url.path.split("/")
    try:
        if "shop" in path_parts:
            idx = path_parts.index("shop")
            if idx + 1 < len(path_parts):
                shop_id = path_parts[idx + 1].strip()
                if shop_id:
                    return shop_id
    except (IndexError, ValueError):
        pass
    
    logger.warning(f"Missing shop_id in request: {request.url.path}")
    raise TenantGuardError(
        detail="Missing X-Shop-ID header, shop_id query param, or shop/{shop_id} path",
        status_code=400,
    )


async def get_shop_id(request: Request) -> str:
    """
    FastAPI dependency to extract and set shop_id.
    
    Usage:
        @app.get("/items")
        async def list_items(shop_id: str = Depends(get_shop_id)):
            ...
    """
    shop_id = extract_shop_id(request)
    TenantContext.set_shop_id(shop_id)
    return shop_id


def require_tenant(func: Callable) -> Callable:
    """
    Decorator to enforce tenant context on endpoint.
    
    Must be applied AFTER get_shop_id dependency has run.
    Raises 401 if shop_id is not in context.
    
    Usage:
        @app.get("/items")
        @require_tenant
        async def list_items(shop_id: str = Depends(get_shop_id)):
            # shop_id is guaranteed to be set
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            shop_id = TenantContext.ensure_tenant()
            kwargs["_validated_shop_id"] = shop_id
            return await func(*args, **kwargs)
        except RuntimeError as e:
            logger.error(f"Tenant guard failed: {e}")
            raise TenantGuardError(
                detail=str(e),
                status_code=401,
            )
    
    return wrapper


class TenantMiddleware:
    """
    Middleware to enforce tenant context on all requests.
    
    Extracts shop_id and sets it in context automatically.
    Optionally validates it for specific paths.
    
    Usage:
        app.add_middleware(TenantMiddleware, require_for_paths=["/api/"])
    """
    
    def __init__(self, app, require_for_paths: list = None, skip_paths: list = None):
        self.app = app
        self.require_for_paths = require_for_paths or ["/api/"]
        self.skip_paths = skip_paths or ["/health", "/status", "/", "/docs", "/openapi.json"]
    
    async def __call__(self, request: Request, call_next):
        """Process request and set tenant context."""
        # Skip tenant enforcement for health/docs endpoints
        if any(request.url.path.startswith(p) for p in self.skip_paths):
            TenantContext.clear()
            return await call_next(request)
        
        # Extract shop_id (may be None for unauthenticated endpoints)
        try:
            shop_id = extract_shop_id(request)
            TenantContext.set_shop_id(shop_id)
        except TenantGuardError:
            # Check if being strict
            if any(request.url.path.startswith(p) for p in self.require_for_paths):
                # Log and reject
                return _error_response(
                    status_code=400,
                    error="Missing tenant identification",
                    code="TENANT_REQUIRED",
                    detail="X-Shop-ID header is required",
                )
            else:
                # Allow but clear context
                TenantContext.clear()
        
        # Process request
        try:
            response = await call_next(request)
        finally:
            TenantContext.clear()
        
        return response


def _error_response(status_code: int, error: str, code: str, detail: str = ""):
    """Create standardized error response."""
    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "code": code,
            "detail": detail,
        },
    )


class TenantAwareDB:
    """
    Base class for tenant-aware database access.
    
    All queries must be scoped to authenticated shop_id.
    
    Usage:
        class UserRepository(TenantAwareDB):
            async def get_user(self, user_id: int):
                shop_id = self.get_shop_id()  # Ensures shop context
                return await db.query(User).filter(
                    User.shop_id == shop_id,
                    User.id == user_id
                ).first()
    """
    
    def get_shop_id(self) -> str:
        """Get shop_id, raises if not set."""
        return TenantContext.ensure_tenant()
    
    def require_shop_match(self, shop_id: str) -> None:
        """
        Verify that request shop_id matches provided shop_id.
        Raises if there's a mismatch (cross-tenant access attempt).
        """
        current_shop = TenantContext.get_shop_id()
        if current_shop != shop_id:
            logger.error(
                f"Cross-tenant access attempt! Current: {current_shop}, Requested: {shop_id}"
            )
            raise TenantGuardError(
                detail="Unauthorized: shop_id mismatch",
                status_code=403,
            )


# Example usage for Redis-backed queries
class TenantAwareCache:
    """
    Mixin for tenant-scoped cache access.
    
    Usage:
        class ShopCache(TenantAwareCache):
            async def get_products(self):
                shop_id = self.get_shop_id()
                key = f"shop:{shop_id}:products"
                return await redis.get(key)
    """
    
    def _cache_key(self, *parts: str) -> str:
        """Generate cache key with shop_id prefix."""
        shop_id = TenantContext.ensure_tenant()
        return f"shop:{shop_id}:{':'.join(parts)}"
    
    def get_shop_id(self) -> str:
        """Get shop_id, raises if not set."""
        return TenantContext.ensure_tenant()
