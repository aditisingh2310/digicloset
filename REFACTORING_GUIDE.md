# Monorepo Refactoring Guide

## Summary of Changes

This document outlines the refactoring from a scattered experimental structure to a clean, production-ready monorepo.

## What Was Removed

The following experimental and deprecated directories have been removed:

- `enterprise_upgrade_pack/` - Experimental enterprise features
- `enterprise_upgrade_pack_v3/` - Deprecated version
- `digicloset-upgrade-pack/` - Dev scaffold
- `digicloset-upgrade-pack-complete/` - Old upgrade pack
- `digi_upgrade_pack/` - Duplicate scaffold
- `digi_reorg_scaffold/` - Experimental reorganization
- `archive/` - Old archived code
- `docs_ops_clear/` - Outdated documentation
- `frontend_clear/` - Old frontend experiment
- `digicloset_shopify_revenue_features/` - Moved into main app
- `security_hardening_pack_v1/` - Integrated into main services
- `ai-service-layer/` - Consolidated with primary AI service

## What Was Moved

### From `/app` → `/apps/shopify-app/backend`

The main FastAPI application moved to the new Shopify app structure:

```
app/
├── ai/                 → apps/shopify-app/backend/ai/
├── api/                → apps/shopify-app/backend/api/
├── core/               → apps/shopify-app/backend/core/
├── db/                 → apps/shopify-app/backend/db/
├── middleware/         → apps/shopify-app/backend/middleware/
├── models/             → apps/shopify-app/backend/models/
├── optimizations/      → apps/shopify-app/backend/optimizations/
├── routes/             → apps/shopify-app/backend/routes/
├── services/           → apps/shopify-app/backend/services/
├── utils/              → apps/shopify-app/backend/utils/
└── main.py             → apps/shopify-app/backend/main.py
```

### From `/ai_service` → `/services/ai-service`

AI recommendation engine moved to dedicated service:

```
ai_service/
├── embeddings/         → services/ai-service/embeddings/
├── indexing/           → services/ai-service/indexing/
├── recommendation/     → services/ai-service/recommendation/
├── vector_db/          → services/ai-service/vector_db/
├── api/                → services/ai-service/api/
├── main.py             → services/ai-service/main.py
└── requirements.txt    → services/ai-service/requirements.txt
```

### From `/shopify-app-core` → `/apps/shopify-app`

Shopify integration moved to app directory:

```
shopify-app-core/
├── index.js            → apps/shopify-app/index.js (OAuth backend)
├── widget.js           → apps/shopify-app/widget.js (Storefront widget)
├── admin-ui/           → apps/shopify-app/admin-ui/
├── package.json        → apps/shopify-app/package.json
└── shopify.config.js   → apps/shopify-app/shopify.config.js
```

### From `/backend` → `/apps/shopify-app/billing`

Billing logic moved to Shopify app:

```
backend/
├── billing_service.py  → apps/shopify-app/billing/billing_service.py
├── metrics_service.py  → apps/shopify-app/billing/metrics_service.py
├── catalog_service.py  → apps/shopify-app/billing/catalog_service.py
└── config/             → apps/shopify-app/billing/config/
```

### From `/inference_service` → `/services/inference-service`

Inference service moved to services directory:

```
inference_service/
├── main.py             → services/inference-service/main.py
└── requirements.txt    → services/inference-service/requirements.txt
```

### From `/worker.py` → `/services/queue-worker/worker.py`

Background job processor:

```
worker.py              → services/queue-worker/worker.py
```

### From `/jobs` → `/packages/shared/jobs`

Shared job definitions moved to shared packages:

```
jobs/
├── redis_conn.py       → packages/shared/jobs/redis_conn.py
├── ai_jobs.py          → packages/shared/jobs/ai_jobs.py
└── ...                 → packages/shared/jobs/...
```

### From `/prisma` → `/packages/database`

Database schema moved to database package:

```
prisma/
└── schema.prisma      → packages/database/schema.prisma
```

### From `/config` → `/packages/shared/config`

Configuration files moved to shared package:

```
config/
├── config.json         → packages/shared/config/config.json
├── feature_flags.json  → packages/shared/config/feature_flags.json
└── ...                 → packages/shared/config/...
```

---

## What Was Created

### New Shared Packages

**`/packages/shared`** - Core shared utilities:

```
packages/shared/
├── __init__.py
├── config.py           # Centralized configuration management
├── logging.py          # Structured JSON logging
├── types.py            # Pydantic models and schemas
├── exceptions.py       # Custom exception classes
├── redis_utils.py      # Redis connection and caching utilities
├── requirements.txt    # Shared dependencies
└── jobs/               # Job definitions and utilities
```

**`/packages/database`** - Database package:

```
packages/database/
└── schema.prisma       # Prisma ORM schema
```

**`/packages/storage`** - Storage adapters:

```
packages/storage/
├── __init__.py
├── base.py            # Abstract storage interface
├── local.py           # Local filesystem adapter
└── s3.py              # Amazon S3 adapter
```

### New Infrastructure

**`/infra/docker`** - Service Dockerfiles:

```
infra/docker/
├── Dockerfile.shopify-app         # Main app container
├── Dockerfile.ai-service          # AI service container
├── Dockerfile.inference-service   # Inference service container
└── Dockerfile.queue-worker        # Queue worker container
```

**`/infra/k8s`** - Kubernetes manifests:

```
infra/k8s/
├── shopify-app-deployment.yaml
├── ai-service-deployment.yaml
├── inference-service-deployment.yaml
├── queue-worker-deployment.yaml
├── postgres-statefulset.yaml
├── redis-deployment.yaml
└── ingress.yaml
```

**`/infra/ci-cd`** - CI/CD pipelines (moved from `cicd-workflows/`)

---

## Import Changes

### Updating Imports After Refactoring

All code now uses absolute imports from the monorepo root.

#### Before (Old Structure):

```python
# From app/main.py
from app.api.router import api_router
from app.core.config import settings
from app.db.models import Shop

# From ai_service/main.py
from ai_service.embeddings import CLIPEmbedder
from ai_service.utils import setup_logging
```

#### After (New Structure):

```python
# From apps/shopify-app/backend/main.py
from packages.shared.config import config
from apps.shopify_app.backend.api.router import api_router
from apps.shopify_app.backend.db.models import Shop

# From services/ai-service/main.py
from packages.shared.config import config
from packages.shared.logging import get_logger
from services.ai_service.embeddings import CLIPEmbedder
```

### Common Import Patterns

**Importing from shared packages:**

```python
# Configuration
from packages.shared.config import config

# Logging
from packages.shared.logging import get_logger, configure_logging

# Types and responses
from packages.shared.types import APIResponse, ErrorResponse, Status
from packages.shared.types import ShopSchema, AiResultSchema, OutfitSchema

# Exceptions
from packages.shared.exceptions import (
    ValidationError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)

# Redis utilities
from packages.shared.redis_utils import (
    get_redis_connection,
    cache_result,
    invalidate_cache,
)

# Job definitions
from packages.shared.jobs.ai_jobs import AnalyzeProductJob
```

**Importing from database package:**

```python
# Prisma client (after generate)
from packages.database.prisma_client import PrismaClient
```

**Importing from storage package:**

```python
from packages.storage import get_storage_adapter

# Use
storage = get_storage_adapter()
await storage.upload("key", data)
```

**Importing from services (cross-service):**

```python
# Shopify App → AI Service (via HTTP, not imports!)
import httpx

async def get_recommendations(product_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://ai-service:8001/api/v1/search",
            json={"product_id": product_id}
        )
        return response.json()
```

**Importing within same service:**

```python
# Within apps/shopify-app/backend/
from .api.router import api_router
from .services.ai_service import AIService
from .core.config import settings

# Within services/ai-service/
from .embeddings import CLIPEmbedder
from .recommendation import Recommender
```

---

## Updating Python Path

### For Development

Ensure Python path includes monorepo root:

```bash
export PYTHONPATH=/path/to/digicloset:$PYTHONPATH
```

### In Docker

Already configured in Dockerfiles:

```dockerfile
ENV PYTHONPATH=/app:$PYTHONPATH
```

### In tests/IDEs

Update your IDE's Python path to include the monorepo root.

---

## Migration Checklist

For each service being updated:

- [ ] Update all relative imports to absolute imports
- [ ] Replace local config references with `packages.shared.config`
- [ ] Update logging to use `packages.shared.logging`
- [ ] Update exception handling to use `packages.shared.exceptions`
- [ ] Update type definitions to use `packages.shared.types`
- [ ] Update Redis connections to use `packages.shared.redis_utils`
- [ ] Test all imports work with `python -c "import module"`
- [ ] Run tests: `pytest`
- [ ] Build Docker image: `docker build -f infra/docker/Dockerfile.xxx .`

---

## Running Services

### Local Development (Docker Compose)

```bash
docker-compose -f docker-compose.dev.yml up
```

All services will start with hot reload enabled.

### Running Individual Services

**Shopify App:**
```bash
cd apps/shopify-app/backend
PYTHONPATH=/path/to/digicloset:$PYTHONPATH \
uvicorn main:app --port 8000 --reload
```

**AI Service:**
```bash
cd services/ai-service
PYTHONPATH=/path/to/digicloset:$PYTHONPATH \
uvicorn main:app --port 8001 --reload
```

**Queue Worker:**
```bash
cd services/queue-worker
PYTHONPATH=/path/to/digicloset:$PYTHONPATH \
python worker.py
```

---

## Database Setup

### Initial Setup

```bash
cd packages/database

# Generate Prisma client
npx prisma generate

# Run migrations
npx prisma migrate deploy

# Or create database from schema
npx prisma db push
```

### Accessing Database

All services use `DATABASE_URL` from `.env`:

```python
from packages.shared.config import config

db_url = config.DATABASE_URL
# postgresql://digicloset:digicloset_dev@localhost:5432/digicloset
```

---

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update with actual values:
   ```
   SHOPIFY_API_KEY=your-key
   SHOPIFY_API_SECRET=your-secret
   DATABASE_URL=postgresql://user:password@host:5432/digicloset
   REDIS_URL=redis://localhost:6379/0
   ```

3. Load environment:
   ```bash
   set -a
   source .env
   set +a
   ```

---

## Troubleshooting

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'packages.shared'`

**Solution:** Ensure `PYTHONPATH` includes monorepo root:
```bash
export PYTHONPATH=/path/to/digicloset:$PYTHONPATH
```

### Service Connection Issues

**Error:** `ConnectionError: HTTPConnectError to http://ai-service:8001`

**Solution:** In development, use `localhost`:
```python
ai_service_url = "http://localhost:8001"  # Development
ai_service_url = "http://ai-service:8001"  # Docker/K8s
```

### Prisma Client Not Found

**Error:** `ModuleNotFoundError: prisma not found`

**Solution:** Generate Prisma client:
```bash
cd packages/database
npx prisma generate
```

### Database Connection

**Error:** `FATAL: remaining connection slots reserved for non-replication superuser connections`

**Solution:** Check database is running and `DATABASE_URL` is correct.

---

## Next Steps

1. ✅ Clean repository structure created
2. ✅ All code consolidated into services/packages
3. ✅ Shared utilities extracted
4. ✅ Docker and deployment files created
5. ⏳ Update imports in all service files (in progress)
6. ⏳ Test all services locally
7. ⏳ Update CI/CD pipelines if needed
8. ⏳ Document any API changes

---

## Performance Notes

- No performance impact from monorepo structure
- Services still run independently
- Shared code is imported, not duped
- Docker images are built per-service for efficiency
- Local development is simplified with docker-compose

---

## Support

For questions about the new structure or specific import patterns, refer to `ARCHITECTURE.md` or inline code comments.
