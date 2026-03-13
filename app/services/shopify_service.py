"""Tenant-aware Shopify service wrapper with retry-safe API access."""

from typing import Any, Dict, Optional

from app.services.shopify_client import ShopifyClient
from app.core.tenant import TenantContext
from app.core.config import settings


class ShopifyService:
    """Service layer for tenant-scoped Shopify Admin API operations."""

    def _client_for_tenant(self, tenant: TenantContext) -> ShopifyClient:
        return ShopifyClient(tenant.shop_domain, tenant.access_token, api_version=settings.shopify_api_version)

    def get_products(self, tenant: TenantContext, limit: int = 10, request_id: Optional[str] = None) -> Dict[str, Any]:
        client = self._client_for_tenant(tenant)
        resp = client.request(
            "GET",
            f"/admin/api/{settings.shopify_api_version}/products.json?limit={limit}",
            request_id=request_id,
        )
        return resp.json()

    def create_product(
        self,
        tenant: TenantContext,
        payload: Dict[str, Any],
        idempotency_key: str | None = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = self._client_for_tenant(tenant)
        resp = client.request(
            "POST",
            f"/admin/api/{settings.shopify_api_version}/products.json",
            json=payload,
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
        return resp.json()
