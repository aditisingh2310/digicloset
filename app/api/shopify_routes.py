from __future__ import annotations

import json
import logging
from fastapi import APIRouter, Depends, Request, HTTPException

from app.core.tenant import get_tenant_from_request, TenantContext
from app.services.shopify_service import ShopifyService

router = APIRouter(prefix="/shopify", tags=["shopify"])

service = ShopifyService()
logger = logging.getLogger(__name__)


@router.get("/products")
def list_products(request: Request, tenant: TenantContext = Depends(get_tenant_from_request)):
    """Tenant-scoped products route with short TTL caching for repeated queries."""
    redis_client = getattr(request.app.state, "redis", None)
    cache_key = f"shopify:products:{tenant.shop_domain}:10"

    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    request_id = getattr(request.state, "request_id", None)
    try:
        result = service.get_products(tenant, limit=10, request_id=request_id)
    except Exception as exc:
        logger.exception("Failed to fetch products for %s", tenant.shop_domain)
        raise HTTPException(status_code=502, detail="shopify_api_unavailable") from exc

    if redis_client:
        redis_client.setex(cache_key, 60, json.dumps(result))
    return result
