# Webhooks

This document lists the Shopify webhooks used by DigiCloset, describes how payloads are used, and explains idempotency and recovery behavior.

## Webhooks (topics)

The app registers or expects the following webhook topics in merchant stores:

- `app/uninstalled` (implemented)
- `customers/data_request` (implemented intake/audit path)
- `customers/redact` (implemented intake/audit path)
- `shop/redact` (implemented)
- `products/create` (recommended / used by product-sync flows)
- `products/update` (recommended / used by product-sync flows)
- `orders/create` (optional — used only if billing or order-triggered flows are enabled)

Note: the active webhook registration path is in `app/api/oauth.py`, which registers the uninstall and GDPR compliance topics against the root backend. Product webhooks are implied by the product sync/optimization code paths (`app/optimizations/` and `app/optimizations/adapters/shopify.py`) and should be registered during install if those flows are enabled.

## How payloads are used

- `app/uninstalled`:
  - Purpose: Remove merchant credentials and stored merchant-specific data.
  - Payload: Shop domain and metadata are used to identify the merchant account to clean up.
  - Implementation: The webhook endpoint acknowledges the webhook and enqueues or executes store cleanup (deleting tokens, mappings, billing records, feedback entries).

- `customers/data_request`:
  - Purpose: Record and process a GDPR access request.
  - Payload: The customer and request payload are recorded for compliance handling.
  - Implementation: The active worker records the request for audit and review. The current backend does not maintain a dedicated customer profile store in its primary database, so fulfillment requires validating what data is actually held before final response handling.

- `customers/redact`:
  - Purpose: Process customer-level redaction without uninstalling the merchant.
  - Payload: Customer identifiers are used to record the redact request.
  - Implementation: The active worker records the request and completes a no-shop-delete audit path. It must not wipe merchant-scoped shop data.

- `shop/redact`:
  - Purpose: Remove shop-level personal data after Shopify's shop-redact event.
  - Payload: Shop identifiers are used to locate merchant-scoped records.
  - Implementation: The worker follows the shop cleanup path used for uninstall-level merchant data deletion.

- `products/create` / `products/update`:
  - Purpose: Trigger catalog re-indexing or re-analysis so AI-generated outfit bundles remain in sync with the merchant catalog.
  - Payload: The product resource (id, title, variants, images) is used to update internal product mapping or to schedule a re-run of the recommendation pipeline.

- `orders/create`:
  - Purpose (optional): Support analytics, conversion tracking, or billing events if configured.
  - Payload: The order payload can be used to record revenue-attribution events or for usage-based billing calculation.

## Idempotency and retry handling

- Shopify will retry webhook deliveries on non-2xx responses. To avoid duplicate processing the backend:
  - Verifies webhook signatures (HMAC) to authenticate payloads before processing.
  - Uses idempotency keys derived from resource id + topic + delivery timestamp, or persistent webhook delivery IDs if available, to detect and ignore duplicate deliveries.
  - Writes minimal, idempotent updates (e.g., enqueueing a reindex job or upserting product metadata) so repeated deliveries do not create inconsistent state.

## Failure and recovery behavior

- On transient failures (e.g., queue unavailable or downstream DB unavailable) the webhook handler returns a non-2xx response so Shopify will retry the delivery according to its retry policy.
- For long-running work (heavy re-indexing or AI tasks) the webhook handler should enqueue an asynchronous job and return 200 immediately to acknowledge receipt.
- If the app detects repeated failures for the same webhook topic and shop, the monitoring/alerting pipeline should notify the maintainers and/or the merchant via the admin UI.

## Endpoints (examples)

- `POST /api/webhooks/app-uninstalled` — receives uninstall notifications from Shopify.
- `POST /api/webhooks/customers/data_request` — GDPR data request notifications.
- `POST /api/webhooks/customers/redact` — GDPR customer redact notifications.
- `POST /api/webhooks/shop/redact` — GDPR shop redact notifications.
- `POST /webhooks/products/create` — recommended; handler should enqueue product sync job.
- `POST /webhooks/products/update` — recommended; handler should upsert product data and re-schedule analysis.
- `POST /webhooks/orders/create` — optional; used for analytics or usage billing events.
