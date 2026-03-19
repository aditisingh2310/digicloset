# Store Validation Runbook (Production Hardening)

This runbook is for **real Shopify store testing** to confirm no broken UI paths, stable theme extension behavior, and no storefront interference.

## Preconditions
- Use a **dev or staging store** (never production).
- App deployed over HTTPS with real `SHOPIFY_API_KEY`/`SHOPIFY_API_SECRET`.
- Redis + database available.
- A test product with images exists in the store.

## Theme Coverage
Default coverage:
- Dawn
- Sense
- Taste

If your store uses different themes, validate those instead.

## Install + OAuth
1. Install from `/api/auth/install?shop=<shop>.myshopify.com`.
2. Complete OAuth and verify app loads.
3. Confirm webhooks are registered under Shopify Admin → Notifications → Webhooks.

## Dashboard & Settings
1. Open the embedded app dashboard.
2. Load `/api/merchant/dashboard` via the UI and confirm numbers render.
3. Toggle widget on/off and confirm `/api/merchant/settings` returns updated state.

## Webhook Handling
1. Trigger **app/uninstalled** by uninstalling the app in Shopify Admin.
2. Verify the webhook response is **2xx** and that sessions are revoked:
   - Redis keys `session:*` removed for that shop.
   - Shop token cleared in DB (`shops.access_token` empty, `uninstalled_at` set).
3. Reinstall and verify access is restored and webhooks re-register.

## Theme Extension (No Storefront Interference)
1. Add the DigiCloset badge block to a product template.
2. Validate the badge renders only when the metafield exists.
3. Inspect page styles and confirm no global CSS changes (fonts, buttons, body styles).
4. Toggle the widget setting and confirm storefront behavior updates as expected.

## Storefront Widget Stability
1. Load a product page with the widget container.
2. Verify widget mounts into its container and does not alter layout outside it.
3. Check for console errors and verify no DOM nodes are injected outside the container.

## Performance Smoke
Use Locust (`python/scripts/locustfile.py`) with environment variables:
- `SHOP_DOMAIN`
- `ACCESS_TOKEN`

Targets:
- p95 < 500ms non‑AI endpoints
- p95 < 2s AI endpoints
- 50 concurrent users
- 1k webhook deliveries/day (simulate in staging)

## Evidence to Capture
- Screenshots of widget + badge across themes.
- Logs showing webhook delivery accepted + cleanup completed.
- Locust report summary (p95 latency).
