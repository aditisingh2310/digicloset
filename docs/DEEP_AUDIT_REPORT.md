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

- `pytest --collect-only -q`
- `pytest tests -o addopts=`
- `pytest --cov=app --cov=jobs --cov-report=term-missing tests -q`

Result:

- `43 passed, 3 skipped, 46 warnings in 19.01s`
- Coverage total: `50%`

Known skips:

- `tests/test_ai_jobs.py` requires `fakeredis`
- `tests/unit/test_end_to_end.py` requires a running integration API

Key warning buckets:

- Pydantic v2 deprecation warnings in `app/utils/abuse_protection.py`
- FastAPI lifespan deprecations in `app/main.py`
- event-loop deprecation warnings in `tests/test_billing.py`

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

### Fixed During This Audit

- `customers/redact` no longer follows the uninstall cleanup path
- GDPR data requests now create a structured internal audit record instead of only logging
- customer-redact requests now create a structured audit record instead of wiping shop data

### Still Partially Implemented

- `customers/data_request` is now recorded for review, but full fulfillment still depends on an operational compliance response process
- staging/dev-store GDPR validation is still blocked until a real Shopify dev or staging store is available

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

### P2

- clean up Pydantic v2 deprecations
- reduce bundle size warnings in the storefront widget
- reduce confusion from legacy duplicate app trees
