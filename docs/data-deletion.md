# Data Deletion and GDPR Handling

This document explains what DigiCloset stores, what happens on uninstall and redact webhooks, and how Shopify GDPR requests are handled in the active backend.

## Merchant Data Stored by the Active Backend

Examples of merchant-scoped data present in the active backend include:

- OAuth tokens and server-side sessions required to call Shopify APIs.
- Billing and usage records.
- Merchant support and feedback records.
- Product and try-on related operational data needed to provide the service.
- Webhook delivery metadata and security/observability logs.

The active backend is designed primarily around merchant and store data. It does not maintain a dedicated customer profile store in its main application database.

## Uninstall and Shop Redact

On `app/uninstalled` and `shop/redact`, DigiCloset is designed to:

- revoke stored access tokens;
- revoke server-side sessions;
- mark the shop as uninstalled;
- remove merchant-scoped subscriptions, usage events, and credit balances;
- record a deletion audit event.

Cleanup is triggered immediately when the webhook worker processes the event. The HTTP webhook endpoint may acknowledge receipt before cleanup finishes so the request path stays fast and retry-safe.

## Customer Data Request

On `customers/data_request`, DigiCloset records the request for compliance review and response handling. The active backend records the request payload and customer identifiers for audit purposes.

Because the active backend does not maintain a dedicated customer profile store, the current workflow is:

- accept and authenticate the webhook;
- record the request for review;
- confirm what customer-related data is actually held before completing a final response through the merchant's compliance process.

## Customer Redact

On `customers/redact`, DigiCloset records the redact request and completes a no-shop-delete audit path. A customer redact request must not behave like `app/uninstalled`.

In the active backend, the customer-redact worker:

- records the request details for audit;
- does not revoke the entire shop installation;
- does not wipe merchant-scoped shop data as part of customer-level redaction.

## Post-Uninstall Persistence

After uninstall or shop-redact cleanup completes, DigiCloset is designed not to retain merchant access tokens, active sessions, or merchant-scoped operational records tied to the removed shop, except where retention is required for legal, security, or accounting reasons.
