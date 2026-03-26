from __future__ import annotations

from fastapi import Request, HTTPException
from typing import Callable

from app.services.billing_service import BillingService


async def billing_enforcement_middleware(request: Request, call_next: Callable):
    """Middleware to enforce billing for protected routes.

    Expects `request.state.tenant` to be set by tenant middleware.
    Allows billing endpoints and public endpoints.
    """
    path = request.url.path
    # Allow public app surfaces and docs to pass through without tenant context.
    allow_paths = {
        "/",
        "/privacy",
        "/terms",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }
    allow_prefixes = (
        "/api/billing",
        "/api/webhooks",
        "/health",
        "/api/auth",
    )
    if path in allow_paths or any(path.startswith(p) for p in allow_prefixes):
        return await call_next(request)

    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(status_code=401, detail="Missing tenant")

    store = getattr(request.app.state, "store", None)
    db = getattr(request.state, "db", None)
    backend = store or db
    if backend is None:
        raise HTTPException(status_code=500, detail="Database not available")

    svc = BillingService(tenant.shop_domain, tenant.access_token, backend)
    allowed = await svc.is_active_or_in_trial()
    if not allowed:
        raise HTTPException(status_code=402, detail="subscription_inactive")

    return await call_next(request)
