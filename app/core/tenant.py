from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context representing a Shopify shop.

    Fields:
    - shop_domain: the myshopify domain (e.g., store.myshopify.com)
    - access_token: shop access token for API calls
    - shop_id: optional numeric id for DB scoping
    """
    shop_domain: str
    access_token: str
    shop_id: Optional[int] = None


async def tenant_middleware(request: Request, call_next):
    """FastAPI middleware to extract tenant information from each request.

    Supports two authentication flows:
    1. Shopify API calls: `x-shopify-shop-domain` + `authorization: Bearer <token>`
    2. Embedded app session cookie: `session_id` cookie referencing Redis session.

    Attaches `TenantContext` to `request.state.tenant`.
    Rejects requests missing tenant headers/cookie with 401.
    """
    # Allow health, public docs and webhook endpoints to bypass tenant enforcement
    public_paths = ("/health", "/openapi.json", "/docs", "/redoc")
    if request.url.path in public_paths or request.url.path.startswith("/api/webhooks"):
        return await call_next(request)

    shop = request.headers.get("x-shopify-shop-domain")
    auth = request.headers.get("authorization") or request.headers.get("x-shopify-access-token")

    # If the standard Shopify headers are missing, attempt cookie-based session lookup
    if not shop or not auth:
        session_id = request.cookies.get("session_id")
        if session_id and getattr(request.app.state, "redis", None):
            session_data = request.app.state.redis.get(f"session:{session_id}")
            if session_data:
                try:
                    session_json = json.loads(session_data)
                    shop = session_json.get("shop")
                    auth = session_json.get("access_token")
                except Exception:
                    shop = None
                    auth = None

    if not shop or not auth:
        raise HTTPException(status_code=401, detail="Missing shop or access token")

    # support 'Bearer <token>' format
    token = auth.split(" ")[-1]

    tenant = TenantContext(shop_domain=shop, access_token=token)

    # Attach to request state for dependency injection
    request.state.tenant = tenant

    # Attach a structured LoggerAdapter; request_id middleware may override later
    request.state.logger = logging.LoggerAdapter(logger, {"shop_domain": shop})

    # Validate session-shop header if present (defense-in-depth)
    session_shop = request.headers.get("x-session-shop")
    if session_shop and session_shop != shop:
        # mismatched session indicates potential tenant confusion or session fixation
        raise HTTPException(status_code=403, detail="Session shop mismatch")

    response = await call_next(request)
    return response


def get_tenant_from_request(request: Request) -> TenantContext:
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(status_code=500, detail="Tenant context not available")
    return tenant
