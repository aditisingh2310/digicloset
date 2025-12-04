# DigiCloset — Reorganized Scaffold
This scaffold addresses the major limitations found in the original repository by providing a clear monorepo layout, unified Docker + docker-compose, example CI, environment management, and a basic migration pattern.

## What this scaffold includes
- `docker-compose.yml` for local development orchestration (frontend, backend, python-worker, db)
- Single `Makefile` with common commands
- `services/` monorepo layout:
  - `backend/` (Node.js + Express) with unified package.json and README
  - `frontend/` (React + TypeScript minimal app)
  - `worker/` (Python placeholder for image/ML tasks)
- `infra/` folder: single `Dockerfile` (multi-stage), `env.example`, and migration placeholders
- `.github/workflows/ci.yml` simple CI pipeline example
- `migrations/` placeholder with a recommended pattern
- LICENSE (MIT)

## How to use
1. Copy `.env.example` to `.env` and fill credentials.
2. `make up` to build and run services locally via docker-compose.
3. Use `make test` and `make lint` as basic checks.

---
This scaffold is intentionally minimal — it gives a single source-of-truth structure and the tools to expand safely.
