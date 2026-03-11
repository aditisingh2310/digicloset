# DigiCloset: Shopify AI SaaS Platform

Production-grade Shopify embedded application for AI-powered virtual try-on and outfit recommendations. Built as a clean, scalable monorepo with independent microservices.

## Overview

DigiCloset helps Shopify merchants increase AOV through:
- **AI-Powered Recommendations** - CLIP-based semantic product matching
- **Virtual Try-On** - Image-to-image inference for outfit visualization
- **Smart Bundling** - Automated outfit generation from product catalog
- **Merchant Dashboard** - Analytics, configuration, and bundle management

## Project Structure

This is a **production-ready monorepo** with the following architecture:

```
/apps              → Shopify embedded application
  /shopify-app     → Backend API + OAuth + billing + widget

/services          → Microservices
  /ai-service      → Recommendation engine (CLIP embeddings, vector DB)
  /inference-service → Virtual try-on via Replicate API
  /queue-worker    → Background job processing

/packages          → Shared libraries
  /database        → Prisma ORM schema
  /shared          → Common config, types, utilities
  /storage         → S3/local storage adapters

/frontend          → Frontend applications
  /admin-dashboard → Merchant dashboard
  /shopify-widget  → Storefront widget UI

/infra             → Infrastructure & deployment
  /docker          → Service Dockerfiles
  /k8s             → Kubernetes manifests
  /ci-cd           → CI/CD pipelines
```

**For detailed architecture documentation**, see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <repo-url>
   cd digicloset
   cp .env.example .env
   ```

2. **Start all services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

   Services available at:
   - **Shopify App**: http://localhost:8000
   - **AI Service**: http://localhost:8001
   - **Inference Service**: http://localhost:8002
   - **PostgreSQL**: localhost:5432
   - **Redis**: localhost:6379

3. **Run database migrations:**
   ```bash
   cd packages/database
   npx prisma migrate deploy
   ```

### Running Individual Services

**Shopify App:**
```bash
cd apps/shopify-app/backend
uvicorn main:app --port 8000 --reload
```

**AI Service:**
```bash
cd services/ai-service
uvicorn main:app --port 8001 --reload
```

**Queue Worker:**
```bash
cd services/queue-worker
python worker.py
```

## API Endpoints

### Shopify App (http://localhost:8000)

**Product Analysis:**
- `POST /api/v1/analyze` - Analyze product and generate recommendations
- `GET /api/v1/products` - List products with recommendations
- `POST /api/v1/bundles` - Create outfit bundle

**Merchant Dashboard:**
- `GET /api/v1/merchant/dashboard` - Analytics and metrics
- `GET /api/v1/merchant/settings` - Configuration
- `POST /api/v1/merchant/settings` - Update settings

**Webhooks:**
- `POST /api/v1/webhooks/shopify` - Shopify webhook receiver

### AI Service (http://localhost:8001)

- `POST /api/v1/embeddings` - Generate product embeddings
- `POST /api/v1/search` - Semantic product search
- `POST /api/v1/recommendations` - Get outfit recommendations

### Inference Service (http://localhost:8002)

- `POST /api/v1/tryon` - Generate virtual try-on image
- `GET /api/v1/async-job/{id}` - Check async job status

## Configuration

All services use centralized configuration from `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/digicloset

# Redis
REDIS_URL=redis://localhost:6379/0

# Shopify
SHOPIFY_API_KEY=your-key
SHOPIFY_API_SECRET=your-secret

# AI Settings
CLIP_MODEL_NAME=openai/clip-vit-base-patch32

# External APIs
REPLICATE_API_TOKEN=your-token
```

See `.env.example` for complete configuration options.

## Architecture

### Service Communication

```
Shopify App      AI Service     Inference Service    Queue Worker
    ↓               ↓                  ↓                 ↓
 [FastAPI]    [FastAPI]          [FastAPI]          [RQ]
    ↓               ↓                  ↓                 ↓
±─────────────────────────────────────────────────────────┤
│                 PostgreSQL Database                      │
│                      Redis Queue                         │
└─────────────────────────────────────────────────────────┘
```

### Data Flow: Product Recommendation

1. Merchant uploads product image
2. Shopify App validates and queues job
3. AI Service generates CLIP embeddings
4. Vector DB searches for similar products
5. Results cached and returned to merchant
6. Frontend displays recommendations

### Data Flow: Virtual Try-On

1. Customer selects product in storefront
2. Widget captures image via device camera
3. Inference Service processes via Replicate
4. Result cached in S3/local storage
5. Widget displays try-on result

## Development

### Project Organization

- **Monorepo:** Single repository, multiple independent services
- **Shared Code:** `/packages/shared` for common utilities
- **Configuration:** Centralized in `/packages/shared/config.py`
- **Logging:** Structured JSON logging via `/packages/shared/logging.py`
- **Database:** Prisma ORM with `/packages/database/schema.prisma`

### Adding New Code

**Service-specific code:**
Add to service directory (e.g., `apps/shopify-app/backend/services/`)

**Shared code:**
Add to `/packages/shared/`

**Imports (example):**
```python
from packages.shared.config import config
from packages.shared.logging import get_logger
from packages.shared.types import APIResponse
from packages.shared.exceptions import NotFoundError
```

### Testing

```bash
# All tests
pytest

# Service-specific
pytest apps/shopify-app/backend/tests

# With coverage
pytest --cov=apps --cov=services --cov=packages
```

### Building Docker Images

```bash
# Shopify App
docker build -f infra/docker/Dockerfile.shopify-app -t digicloset-shopify-app .

# AI Service
docker build -f infra/docker/Dockerfile.ai-service -t digicloset-ai-service .

# Inference Service
docker build -f infra/docker/Dockerfile.inference-service -t digicloset-inference-service .

# Queue Worker
docker build -f infra/docker/Dockerfile.queue-worker -t digicloset-queue-worker .
```

## Deployment

### Production Checklist

- [ ] Update `.env` with production secrets
- [ ] Configure PostgreSQL (managed DB recommended)
- [ ] Configure Redis (managed cache recommended)
- [ ] Set up S3 for image storage
- [ ] Configure Shopify API credentials
- [ ] Update `ALLOWED_ORIGINS` for CORS
- [ ] Run database migrations
- [ ] Build and push Docker images
- [ ] Deploy to Kubernetes or container service

### Kubernetes Deployment

Manifests in `/infra/k8s/`:

```bash
kubectl apply -f infra/k8s/postgres-statefulset.yaml
kubectl apply -f infra/k8s/redis-deployment.yaml
kubectl apply -f infra/k8s/shopify-app-deployment.yaml
kubectl apply -f infra/k8s/ai-service-deployment.yaml
kubectl apply -f infra/k8s/inference-service-deployment.yaml
kubectl apply -f infra/k8s/queue-worker-deployment.yaml
kubectl apply -f infra/k8s/ingress.yaml
```

### Environment-Specific Configuration

Set `ENVIRONMENT` variable:
- `development` - Debug mode, verbose logging
- `staging` - Production-like, detailed errors
- `production` - Performance mode, minimal logging

## Monitoring

All services expose:
- **Health checks:** `GET /health`
- **Metrics:** Prometheus format at `GET /metrics`
- **Structured logs:** JSON format with request IDs
- **Error tracking:** Full exception context in logs

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detailed architecture documentation
- [REFACTORING_GUIDE.md](./REFACTORING_GUIDE.md) - Monorepo refactoring details
- [docs/API.md](./docs/API.md) - API documentation

## Contributing

1. Follow monorepo conventions
2. Add shared code to `/packages/shared`
3. Write tests for new features
4. Document API changes in `/docs/API.md`
5. Use type hints throughout

## Support

For architecture questions, see [ARCHITECTURE.md](./ARCHITECTURE.md).
For refactoring details, see [REFACTORING_GUIDE.md](./REFACTORING_GUIDE.md).

## License

See [LICENSE](./LICENSE)
