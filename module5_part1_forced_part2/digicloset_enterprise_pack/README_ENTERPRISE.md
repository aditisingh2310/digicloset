# README_ENTERPRISE.md

This file contains enterprise-focused instructions and guidance to harden, CI-enable, and deploy the Digicloset repository.

## Included files in this pack
- `.github/workflows/ci.yml` — GitHub Actions workflow to run lint/test and build images for Node and Python services.
- `Dockerfile.node` — Multi-stage Dockerfile for the Node.js service (searches `server/` or root `package.json`).
- `Dockerfile.python` — Multi-stage Dockerfile for the Python/FastAPI inference service (searches `inference-service/` or root `requirements.txt`).
- `Dockerfile` — Helper that explains how to use the service-specific Dockerfiles.
- `.env.example` — Template for environment variables you should provide via secret storage in CI and deployment.

## How to use
1. **Place files**: Copy `.github/workflows/ci.yml` into `.github/workflows/ci.yml` at repository root. Copy the Dockerfiles to repository root. Keep the service folder names (`server/`, `inference-service/`) as-is or update the Dockerfile paths accordingly.

2. **Add secrets to GitHub**:
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `REPLICATE_API_TOKEN`
   - `SENTRY_DSN` (optional)
   - `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (if used)
   - Any other DB credentials (do **not** commit secrets to the repo)

3. **Run CI**: Push a branch or open a PR. The workflow will install dependencies, run lint/test (if present), and attempt to build the Docker images. Fix failures and add tests as needed.

4. **Build images locally** (examples):
   - Node: `docker build -f Dockerfile.node -t digicloset-node:local .`
   - Python: `docker build -f Dockerfile.python -t digicloset-python:local .`

## Secret cleanup guidance (immediate steps)
1. Search the repo for secrets and rotate any keys found. Helpful commands:
   - `git grep -n -- 'api[_-]?key\|secret\|password\|access[_-]?token' || true`
   - `trufflehog filesystem --entropy=True .` (install trufflehog)
   - `git log --pretty=format:'%H' | while read rev; do git grep -n 'REPLICATE' $rev || true; done`

2. If you find secrets in Git history:
   - Remove them using `git filter-repo` or `git filter-branch` (prefer `git filter-repo`).
   - Rotate the compromised credentials immediately in provider consoles (Supabase, AWS, Replicate, etc.).

3. Add `.env` to `.gitignore` and keep only `.env.example` in repo.

## Next recommended enterprise steps
- Add Dependabot for dependency updates and vulnerability scanning.
- Add automated image scanning in CI (e.g., `aquasecurity/trivy-action`).
- Add a deployment job to push images to your registry (requires credentials/secrets).
- Add policy checks and enforce branch protection rules in GitHub.

---
If you want, I can also:
- Convert these files into a zip for direct upload (already prepared below).
- Create a Dependabot config and a trivy scan step in the workflow.
- Generate a Helm chart scaffold for Kubernetes.