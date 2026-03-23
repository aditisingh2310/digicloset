# Deep Audit Report

Date: March 23, 2026

## Source of Truth

The active audited product surface is:

- root FastAPI app
- root admin UI
- `apps/shopify-widget`

The duplicated Shopify/backend trees under `apps/shopify-app` and `shopify-app-core` are treated as legacy during this audit. They remain relevant as maintenance and CI drift risk, but they are not the source of truth for the tested runtime.

## Automated Run Matrix

### Backend

Commands run:

- `pytest --collect-only -q tests -o addopts=`
- `pytest tests -o addopts=`
- `pytest tests -W error::DeprecationWarning -o addopts=`
- `pytest --cov=app --cov=jobs --cov-report=term-missing tests -q`
- `pytest --cov=app.api.webhooks --cov=jobs.webhook_tasks --cov=app.services.data_deletion --cov=app.services.gdpr_requests --cov-report=term-missing tests -q`
- `pytest tests/test_gdpr_endpoint_variants.py tests/test_gdpr_guardrails.py tests/test_gdpr_worker_paths.py tests/test_gdpr_uninstall.py tests/test_shopify_app_review_flow.py -o addopts=`
- `pytest tests/test_webhook_deep_paths.py tests/test_oauth_webhook_registration.py tests/test_ai_jobs.py -o addopts=`
- `pytest tests/test_shopify_app_config.py -o addopts=`

Result:

- latest full `pytest tests -o addopts=` run: `59 passed, 3 skipped`
- strict deprecation pass: `59 passed, 3 skipped`
- additional targeted deep webhook/GDPR runs passed:
  - `22 passed` in the GDPR/app-review slice
  - `8 passed, 1 skipped` in the deep webhook/OAuth/AI-job slice
- broad coverage total: `50%`
- focused webhook/GDPR coverage total: `87%`

Known skips:

- `tests/test_ai_jobs.py` is now an explicit platform skip on Windows because the installed `rq` package imports a `fork` multiprocessing context that is unavailable on this platform
- `tests/unit/test_end_to_end.py` requires a running integration API; it has been updated to probe the active root app's public routes and OAuth install endpoint instead of stale `/api/v1/*` routes
- `tests/test_shopify_app_config.py` now verifies that the committed Shopify app config preserves the required compliance webhook subscriptions

Key warning buckets:

- Pydantic v2 deprecation warnings in `app/utils/abuse_protection.py`
- FastAPI lifespan deprecations in `app/main.py`
- event-loop deprecation warnings in `tests/test_billing.py`
- raw `data=` upload deprecation warnings from `httpx` in webhook tests

Strict-mode finding:

- `pytest tests -W error::DeprecationWarning -o addopts=` now passes after migrating the abuse-protection models to Pydantic v2 field validation, moving FastAPI startup/shutdown to lifespan handlers, and removing known deprecation-heavy test patterns

### Root Admin UI

Commands run:

- `npm install --no-fund --no-audit`
- `npm run build`
- `npm run type-check`
- `npm run lint`
- `npm run test -- --run`

Result:

- build: pass
- type-check: pass
- lint: pass
- tests: pass (`4` smoke tests)

### Storefront Widget

Commands run:

- `npm install --no-fund --no-audit`
- `npm run build`
- `npm run type-check`
- `npm run lint`
- `npm test`

Result:

- build: pass
- type-check: pass
- lint: pass
- tests: pass (`1` widget smoke test)

## JS Test Inventory

### Active and Trustworthy

- `admin-ui/src/__tests__/admin-smoke.test.jsx`
- `apps/shopify-widget/src/__tests__/widget.spec.ts`

### Legacy or Disconnected

- `tests/unit/api.integration.test.ts`
- `tests/unit/aiService.test.ts`
- `tests/unit/cacheService.test.ts`
- `tests/unit/api_enterprise.test.js`

These files are not part of the active backend pytest run and do not align with the current root frontend test harness. They should not be counted as current protection without a deliberate port or deletion pass.

### Legacy Integration Drift

- `tests/unit/test_end_to_end.py` is a Python integration suite, not a frontend suite, and it currently points to legacy endpoints that do not exist in the active root app
- repo docs still reference old `/api/v1/webhooks/shopify/*` shapes in some places, which increases audit confusion

## CI Parity Findings

Before this audit:

- backend Python tests ran in CI
- widget build ran in CI
- root frontend had no serious CI validation
- widget tests were not part of CI validation

This audit adds CI coverage for:

- root frontend build, lint, type-check, and tests
- widget build, lint, type-check, and tests

## GDPR Verdict

### Implemented

- webhook HMAC validation
- webhook idempotency and retry-safe queue behavior
- uninstall cleanup path
- shop-redact cleanup path
- uninstall/shop cleanup tests
- webhook registration attempt during OAuth
- OAuth callback test proof that all four required topics are attempted during registration
- worker dead-letter handling for terminal webhook failures
- safe non-401/non-503 webhook responses that continue returning a 200-series acknowledgment
- committed `shopify.app.toml` source of truth for required compliance webhook subscriptions

### Fixed During This Audit

- `customers/redact` no longer follows the uninstall cleanup path
- GDPR data requests now create a structured internal audit record instead of only logging
- customer-redact requests now create a structured audit record instead of wiping shop data
- `/privacy` and `/terms` are now public and no longer blocked by tenant or billing middleware

### Still Partially Implemented

- `customers/data_request` is now recorded for review, but full fulfillment still depends on an operational compliance response process
- staging/dev-store GDPR validation is still blocked until a real Shopify dev or staging store is available
- `shopify.app.toml` still contains template placeholders for the real deployed app URL and client id, so the file is now present and structured correctly but still needs environment-specific values before deployment

### Missing Before This Audit and Addressed

- privacy page placeholder content
- terms page placeholder content

## Staging Status

Real Shopify dev-store validation is still pending because no dev-store credentials or live webhook replay environment were available in this audit run.

The existing runbook to finish that validation is:

- `docs/STORE_TEST_RUNBOOK.md`

## Prioritized Backlog

### P0

- complete dev-store GDPR validation with signed webhook replay or live Shopify events
- formalize the operational process for responding to recorded `customers/data_request` requests

### P1

- raise backend coverage above the current `50%`, especially in `app/services/*`, `app/api/*`, and `jobs/*`
- port or delete the disconnected JS tests under `tests/unit`
- migrate FastAPI startup/shutdown handling to lifespan
- replace the template values in `shopify.app.toml` with the real deployed app identifiers and URLs before release
- decide whether Windows is a supported worker/test platform and, if so, pin or replace the current `rq` path

### P2

- clean up Pydantic v2 deprecations
- reduce bundle size warnings in the storefront widget
- reduce confusion from legacy duplicate app trees
