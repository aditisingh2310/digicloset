# DigiCloset Monorepo Architecture

## Overview

DigiCloset is a production-grade Shopify AI SaaS application built as a clean monorepo. The project is organized into clear, independent services that communicate through HTTP APIs and message queues, with shared packages for common functionality.

## Directory Structure

```
digicloset/
├── apps/                      # Main applications
│   └── shopify-app/          # Shopify embedded app + backend API
│       ├── backend/          # FastAPI backend server
│       ├── billing/          # Stripe billing integration
│       └── widget/           # Storefront widget (JavaScript)
│
├── services/                  # Microservices
│   ├── ai-service/           # Recommendation engine (CLIP embeddings, vector DB)
│   ├── inference-service/    # Virtual try-on inference (Replicate API integration)
│   └── queue-worker/         # RQ-based background job processor
│
├── packages/                  # Shared libraries
│   ├── database/             # Prisma schema and migrations
│   ├── shared/               # Shared utilities, config, types
│   │   ├── config.py        # Centralized configuration
│   │   ├── logging.py       # Structured logging
│   │   ├── types.py         # Pydantic models and schemas
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── redis_utils.py   # Redis connection and caching
│   └── storage/              # S3/local storage adapters
│
├── frontend/                  # Frontend applications
│   ├── admin-dashboard/      # Merchant dashboard (React/Vite)
│   └── shopify-widget/       # Storefront widget UI
│
├── infra/                     # Infrastructure & deployment
│   ├── docker/               # Dockerfiles for each service
│   ├── k8s/                  # Kubernetes manifests
│   └── ci-cd/                # GitHub Actions, CI/CD pipelines
│
├── docs/                      # Documentation
│   └── API.md               # API documentation
│
├── scripts/                   # Development and utility scripts
└── docker-compose.dev.yml    # Local development compose file
```

## Service Architecture

### 1. Shopify App (`/apps/shopify-app`)

**Purpose:** Main Shopify embedded application and backend API

**Components:**
- **Backend** (`/apps/shopify-app/backend`) - FastAPI server
  - OAuth flow and webhook handlers
  - Product analysis and recommendation endpoints
  - Merchant API (dashboard, analytics, settings)
  - Integration with AI services via HTTP

- **Billing** (`/apps/shopify-app/billing`) - Stripe integration
  - Subscription management
  - Usage tracking and metering
  - Billing webhooks

- **Widget** (`/apps/shopify-app/widget`) - JavaScript storefront widget
  - Try-on UI component
  - Product recommendations display
  - Async generation progress tracking

**Key Endpoints:**
- `POST /api/v1/analyze` - Analyze product and generate recommendations
- `GET /api/v1/products` - List products with recommendations
- `POST /api/v1/bundles` - Create outfit bundle
- `GET /api/v1/merchant/dashboard` - Merchant analytics
- `POST /api/v1/webhooks/shopify` - Shopify webhook receiver

**Technologies:** FastAPI, Python 3.11, Pydantic

**Port:** 8000

---

### 2. AI Service (`/services/ai-service`)

**Purpose:** Recommendation engine with CLIP embeddings and vector search

**Components:**
- **Embeddings** - CLIP model for product image analysis
- **Vector Database** - FAISS for similarity search
- **Embeddings Indexing** - Build and maintain product catalog index
- **Recommendation Engine** - Generate outfit recommendations

**Key Features:**
- Semantic product matching using vision-language model
- Fast approximate nearest neighbor search
- Real-time catalog indexing
- Multi-tenant isolation (per-shop indexes)

**API Endpoints:**
- `POST /api/v1/embeddings` - Generate embeddings for image
- `POST /api/v1/search` - Semantic product search
- `POST /api/v1/recommendations` - Get outfit recommendations
- `POST /api/v1/reindex` - Rebuild shop's product index

**Technologies:** FastAPI, PyTorch, CLIP, FAISS, NumPy

**Port:** 8001

---

### 3. Inference Service (`/services/inference-service`)

**Purpose:** Virtual try-on and advanced inference via external APIs

**Components:**
- Replicate API integration for image-to-image models
- Async job management
- Result caching and optimization

**Planned Endpoints:**
- `POST /api/v1/tryon` - Generate virtual try-on image
- `POST /api/v1/async-job/{id}` - Check async job status
- `GET /api/v1/models` - List available inference models

**Technologies:** FastAPI, Replicate SDK, Async workers

**Port:** 8002

---

### 4. Queue Worker (`/services/queue-worker`)

**Purpose:** Background job processing for long-running tasks

**Technologies:** RQ (Redis Queue), Python

**Job Types:**
- Product catalog indexing
- Bulk recommendation generation
- Image processing
- Webhook delivery retry

**Queues:**
- `ai` - AI/recommendation jobs
- `default` - General tasks

**Configuration:**
```bash
RQ_QUEUES=ai,default python services/queue-worker/worker.py
```

---

## Shared Packages

### 1. Shared (`/packages/shared`)

**Core utilities used by all services:**

- **config.py** - Centralized configuration management
  - Environment variable handling
  - Configuration validation
  - Service-specific settings

- **logging.py** - Structured JSON logging
  - Configurable log levels
  - Request ID tracking
  - Exception formatting

- **types.py** - Pydantic models and schemas
  - `APIResponse[T]` - Standard API response format
  - `ErrorResponse` - Standard error format
  - Domain models (Shop, AiResult, Outfit, etc.)

- **exceptions.py** - Custom exception classes
  - `ValidationError`, `AuthenticationError`, `AuthorizationError`
  - `NotFoundError`, `RateLimitError`, `ExternalServiceError`
  - Standard error serialization

- **redis_utils.py** - Redis connection and utilities
  - Connection pooling
  - Caching decorators
  - Cache invalidation

### 2. Database (`/packages/database`)

**Prisma ORM and schema:**
- `schema.prisma` - PostgreSQL schema definition
- Migrations in `/prisma/migrations`
- Models for:
  - `Shop` - Merchant information
  - `AiResult` - Analysis results cache
  - `Outfit` - Outfit bundle definitions

**Usage in services:**
```bash
# Generate Prisma client
npx prisma generate

# Run migrations
npx prisma migrate deploy
```

### 3. Storage (`/packages/storage`)

**Storage adapters for local/S3 storage**

**Supported backends:**
- Local filesystem (`LOCAL_STORAGE_PATH`)
- Amazon S3 (`S3_BUCKET`, `S3_REGION`)

**Interface:**
```python
class StorageAdapter:
    async def upload(self, key: str, data: bytes) -> str
    async def download(self, key: str) -> bytes
    async def delete(self, key: str) -> None
    async def list(self, prefix: str) -> List[str]
```

---

## Communication Patterns

### Service-to-Service Communication

```
┌──────────────────┐
│   Shopify App    │
│    (Port 8000)   │
└────────┬─────────┘
         │
         ├──────────────────────────────────┬──────────────────────────────────┐
         │ HTTP                             │ HTTP                             │ HTTP
         ▼                                  ▼                                  ▼
    ┌─────────────┐               ┌──────────────────┐           ┌──────────────────┐
    │ AI Service  │               │ Inference Service│           │   Queue Worker   │
    │ (Port 8001) │               │   (Port 8002)    │           │  (Via Redis)     │
    └─────────────┘               └──────────────────┘           └──────────────────┘
```

**Shopify App → AI Service:**
- Synchronous HTTP requests for product analysis
- Request timeouts: 30 seconds (configurable)
- Circuit breaker pattern for resilience

**Shopify App → Queue Worker:**
- Async job submission via Redis
- Bulk operations, catalog indexing
- Long-running image processing

**Shopify App → Inference Service:**
- Virtual try-on requests
- Async model execution
- Replicate API bridging

### External Service Integration

```
┌──────────────┐         ┌──────────┐         ┌──────────┐
│ DigiCloset   ├────────▶│ Shopify  │         │ Replicate│
│   Services   │         │   API    │         │   API    │
└──────────────┘         └──────────┘         └──────────┘
       │                                            ▲
       │                      ┌──────────────────────┘
       │                      │
       └─────────────────────▶│
              Redis
      (sessions, cache, queue)
                  │
                  ▼
         ┌──────────────┐
         │ PostgreSQL   │
         │   Database   │
         └──────────────┘
```

---

## Data Flow

### Product Analysis & Recommendation Flow

1. **User uploads product image** to admin dashboard
2. **Shopify App** receives request and:
   - Validates shop authentication
   - Stores image temporarily
   - Submits job to queue

3. **Queue Worker** processes:
   - Generates product embeddings via AI Service
   - Searches catalog for similar products
   - Stores results in database
   - Caches recommendations in Redis

4. **Shopify App** polls for results or uses WebSocket
5. **Frontend** displays recommendations to merchant

### Storefront Try-on Flow

1. **Customer selects product** in Shopify storefront
2. **Widget** captures customer image
3. **Shopify App** gateway receives request
4. **Inference Service** generates try-on via Replicate
5. **Result cached** in S3/local storage
6. **Widget** displays result to customer

---

## Configuration Management

All services use a unified configuration system:

```python
from packages.shared.config import config

# Access configuration:
config.DATABASE_URL
config.REDIS_URL
config.AI_INFERENCE_TIMEOUT
config.SHOPIFY_API_KEY
```

**Configuration sources (by priority):**
1. Environment variables (`.env` file)
2. `Config` class defaults
3. Validation on startup

**Environment Variables:**
- See `.env.example` for complete list
- Critical vars: `DATABASE_URL`, `SHOPIFY_API_KEY`, `REDIS_URL`
- Service-specific: `CLIP_MODEL_NAME`, `REPLICATE_API_TOKEN`

---

## Database Schema

**Key tables:**

```sql
-- Merchant/shop information
CREATE TABLE Shop (
  id INT PRIMARY KEY,
  shopDomain TEXT UNIQUE,
  accessToken TEXT,
  scope TEXT,
  subscriptionStatus TEXT DEFAULT 'inactive',
  installedAt TIMESTAMP
);

-- AI analysis results (cached)
CREATE TABLE AiResult (
  id TEXT PRIMARY KEY,
  shop TEXT,
  productId TEXT,
  requestId TEXT UNIQUE,
  category TEXT,
  tags JSON,
  confidence FLOAT,
  createdAt TIMESTAMP
);
```

**Indexes:** 
- `AiResult` indexed by `(shop, productId, createdAt)` for query performance
- `Shop` indexed by `shopDomain` for OAuth lookups

---

## Deployment

### Local Development

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up

# Services will be available at:
# - Shopify App: http://localhost:8000
# - AI Service: http://localhost:8001
# - Inference Service: http://localhost:8002
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

### Production Deployment

1. **Docker Images:** Build images for each service
   ```bash
   docker build -f infra/docker/Dockerfile.shopify-app -t digicloset-shopify-app .
   docker build -f infra/docker/Dockerfile.ai-service -t digicloset-ai-service .
   docker build -f infra/docker/Dockerfile.inference-service -t digicloset-inference-service .
   docker build -f infra/docker/Dockerfile.queue-worker -t digicloset-queue-worker .
   ```

2. **Kubernetes Deployment:** See `/infra/k8s` for manifests
3. **CI/CD:** See `/infra/ci-cd` for GitHub Actions workflows
4. **Environment Setup:**
   - Create `.env` from `.env.example`
   - Configure production secrets
   - Run database migrations: `prisma migrate deploy`

---

## Development Workflow

### Running Individual Services

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install shared packages + service-specific deps
pip install -r packages/shared/requirements.txt
pip install -r apps/shopify-app/backend/requirements.txt

# Run service
cd apps/shopify-app/backend
uvicorn main:app --reload --port 8000
```

### Adding New Code

**Service-specific code:** Add to service directory
**Shared code:** Add to `/packages/shared`
**Update imports:** Use absolute imports from monorepo root

```python
# Good: service imports from shared
from packages.shared.config import config
from packages.shared.logging import get_logger
from packages.shared.types import APIResponse

# Good: service imports from local directory
from .models import Product
from .services import RecommendationEngine
```

### Running Tests

```bash
# All tests
python -m pytest

# Service-specific
pytest apps/shopify-app/backend/tests
pytest services/ai-service/tests

# With coverage
pytest --cov=apps --cov=services --cov=packages
```

---

## Key Design Decisions

1. **Monorepo vs Microservices:** Monorepo provides easier local development and shared code management while maintaining service independence.

2. **HTTP Communication:** Services talk via HTTP for simplicity and debuggability.

3. **Redis Queue:** RQ provides job queuing without heavy message broker complexity.

4. **Centralized Config:** Single source of truth for all environment variables.

5. **Shared Package:** Common utilities reduce duplication.

6. **Prisma ORM:** Type-safe database access with auto migrations.

7. **Structured Logging:** JSON logs enable centralized log aggregation.

---

## Security Considerations

1. **Environment Variables:** Secrets never committed (use `.env`)
2. **CORS:** Configured per environment via `ALLOWED_ORIGINS`
3. **Authentication:** Shopify OAuth for merchant apps
4. **Rate Limiting:** Via middleware in Shopify App
5. **Database:** All user/product data isolated by `shop_id`
6. **API Keys:** External API keys stored as environment variables

---

## Monitoring & Observability

Services expose:
- **Health checks:** `GET /health` on all services
- **Metrics:** Prometheus-compatible metrics at `/metrics`
- **Structured logs:** JSON logs with request IDs for tracing
- **Error tracking:** Exception details logged with context

---

## Future Enhancements

1. GraphQL API for frontend
2. WebSocket support for real-time progress
3. Multi-region deployment
4. Advanced analytics dashboard
5. Custom model fine-tuning pipeline
6. Webhook event streaming
7. Rate limiting per shop + tier

---

## Contributing

- Follow project layout conventions
- Add shared utilities to `/packages/shared`
- Document new endpoints in `/docs/API.md`
- Use type hints throughout codebase
- Write tests for new features

---

## Support

For architecture questions or refactoring needs, refer to this document and the inline code comments.
