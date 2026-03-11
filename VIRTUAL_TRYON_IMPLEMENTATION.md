# Virtual Try-On Implementation Guide

Complete guide to the DigiCloset Virtual Try-On feature implementation, including architecture, integration points, deployment, and monitoring.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Integration Guide](#integration-guide)
4. [Deployment](#deployment)
5. [Configuration](#configuration)
6. [Monitoring & Logging](#monitoring--logging)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

---

## Architecture Overview

The virtual try-on system is built using a **microservices architecture** with clear separation of concerns:

```
┌─────────────────┐
│  Shopify Store  │
│  (Product Page) │
│                 │
│  ┌───────────┐  │
│  │ Try-On    │  │  <- tryon-widget.js
│  │ Widget    │  │
│  └─────────┬─┘  │
└────────────┼────┘
             │ HTTP/REST
             ▼
┌─────────────────────────────────────┐
│   Shopify App Backend (FastAPI)     │
│   /apps/shopify-app/backend         │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Try-On Routes                │  │
│  │ /api/v1/try-on/*             │  │  <- routes/tryon.py
│  │                              │  │
│  │  ├─ POST /generate           │  │
│  │  ├─ GET  /{id}               │  │
│  │  ├─ GET  /credits/check      │  │
│  │  ├─ GET  /credits/info       │  │
│  │  └─ GET  /history            │  │
│  └─────────┬────────────────────┘  │
│            │                        │
│  ┌─────────▼────────────────────┐  │
│  │ Error Handling Middleware    │  │    <- middleware/tryon_errors.py
│  │                              │  │
│  │ - Validation                 │  │
│  │ - Rate Limiting               │  │
│  │ - Structured Logging         │  │
│  └─────────┬────────────────────┘  │
│            │                        │
│  ┌─────────▼──────────────────────┐│
│  │ Database Layer (Prisma ORM)     ││
│  │ - TryOnGeneration Model          ││
│  │ - ShopCredits Model              ││
│  └──────────────────────────────────┘│
└─────────────────────────────────────┘
             │ Celery
             ▼
┌──────────────────────────────┐
│  Celery Queue Worker         │
│  /services/queue-worker/     │
│                              │
│  ├─ generate_tryon_task      │  <- tryon_tasks.py
│  ├─ cancel_generation        │
│  └─ cleanup_old_generations  │
│                              │
│  Broker: Redis               │
│  Backend: Redis              │
└──────────────┬───────────────┘
               │ HTTP/gRPC
               ▼
┌──────────────────────────────┐
│ Inference Service (FastAPI)  │
│ /services/inference-service/ │
│                              │
│  ┌──────────────────────┐   │
│  │ Try-On Routes        │   │
│  │ /api/v1/*            │   │  <- inference_routes.py
│  │                      │   │
│  │ ├─ POST /generate    │   │
│  │ ├─ GET  /status/{id} │   │
│  │ └─ Health check      │   │
│  └──────────┬───────────┘   │
│             │               │
│  ┌──────────▼────────────┐  │
│  │ TryOnService          │  │  <- tryon_service.py
│  │ (Orchestration)       │  │
│  │                       │  │
│  │ - Image validation    │  │
│  │ - Error handling      │  │
│  └──────┬──────┬─────────┘  │
│         │      │            │
│    ┌────▼─┐┌──▼────┐        │
│    │      ││       │        │
│    ▼      ▼▼       ▼        │
│  ┌────────────────────────┐ │
│  │ ReplicateAPIClient     │ │  <- replicate_client.py
│  │ (Async Polling)        │ │
│  │                        │ │
│  │ - Create prediction    │ │
│  │ - Poll status          │ │
│  │ - Cancel prediction    │ │
│  └────────────────────────┘ │
│           │                 │
│  ┌────────▼────────────────┐│
│  │ StorageService          ││  <- storage_service.py
│  │ (S3 + Local Fallback)    ││
│  │                          ││
│  │ - Download images        ││
│  │ - Save results           ││
│  │ - Delete old images      ││
│  └────────────────────────┘ │
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
    ┌─────────┐  ┌─────────┐
    │ Replicate│  │ S3       │
    │ API      │  │ Storage  │
    └─────────┘  └─────────┘
```

---

## System Components

### 1. Frontend Widget (`tryon-widget.js`)

**Location:** `/apps/shopify-app/shopify-widget/tryon-widget.js`

**Features:**
- Embeds "Try On" button on product pages
- Modal dialog for image upload
- Polling-based result retrieval
- Social media sharing
- Error handling and retry logic

**Installation:**
```html
<!-- Add to Shopify theme footer.liquid -->
<script src="https://digicloset.app/widget/tryon-widget.js"></script>
```

**Configuration:**
```javascript
window.DIGICLOSET_API_URL = 'https://api.digicloset.app';
```

**Key Methods:**
- `generateTryOn()` - Initiates generation
- `pollTryOnResult()` - Polls for result with exponential backoff
- `showResult()` / `showError()` - UI state management

---

### 2. Shopify Backend (`/apps/shopify-app/backend/`)

**API Endpoints:**
```
POST   /api/v1/try-on/generate           - Generate try-on
GET    /api/v1/try-on/{tryon_id}         - Check status
GET    /api/v1/try-on/credits/check      - Check credits
GET    /api/v1/try-on/credits/info       - Credit details
GET    /api/v1/try-on/history            - Generation history
```

**Key Files:**
- `routes/tryon.py` - API endpoint definitions
- `services/storage_service.py` - Image storage abstraction
- `middleware/tryon_errors.py` - Error handling & validation
- `tests/test_tryon.py` - Comprehensive tests

**Authentication:**
All endpoints require Shopify shop token (Bearer token in Authorization header)

---

### 3. Inference Service (`/services/inference-service/`)

**Endpoints:**
```
POST   /api/v1/generate-tryon            - Async generation
GET    /api/v1/status/{prediction_id}   - Replicate status
GET    /health                           - Health check
```

**Key Files:**
- `replicate_client.py` - Replicate API integration with async polling
- `tryon_service.py` - High-level orchestration & validation
- `inference_routes.py` - FastAPI endpoints
- `tests/test_replicate_client.py` - Client tests

**Features:**
- Async image generation via Replicate API
- Polling with configurable timeout (default: 300s)
- Automatic retry on failure
- Result notification callback to Shopify backend

---

### 4. Queue Worker (`/services/queue-worker/`)

**Celery Tasks:**
```python
generate_tryon_task()         - Main generation task
cancel_tryon_task()          - Cancel running generation
cleanup_old_generations()    - Periodic cleanup (daily 2 AM)
```

**Key Files:**
- `tryon_tasks.py` - Celery task definitions

**Features:**
- Distributed task queue with Redis broker
- Automatic retry with exponential backoff (3 retries)
- Task status tracking
- Monitoring via Celery flower

---

### 5. Database Schema (`/packages/database/`)

**Models:**
```prisma
model ShopCredits {
  id                String   @id @default(cuid())
  shopId            String   @unique
  monthlyLimit      Int      @default(100)
  creditsUsed       Int      @default(0)
  creditsRemaining  Int
  resetDate         DateTime
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt
  shop              Shop     @relation(fields: [shopId], references: [id])
}

model TryOnGeneration {
  id                String   @id @default(cuid())
  shopId            String
  productId         String
  userImageUrl      String
  garmentImageUrl   String
  generatedImageUrl String?
  replicateId       String?
  status            String   @default("pending")  // pending|processing|completed|failed
  creditsUsed       Int      @default(1)
  processingTime    Float?
  errorMessage      String?
  completedAt       DateTime?
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt
  shop              Shop     @relation(fields: [shopId], references: [id])

  @@index([shopId, createdAt])
  @@index([status])
}
```

---

## Integration Guide

### Step 1: Setup Environment Variables

Create `/apps/shopify-app/.env`:

```bash
# API Configuration
API_BASE_URL=http://localhost:8000

# Replicate API
REPLICATE_API_TOKEN=<your-replicate-token>
REPLICATE_MODEL_ID=replicate-api/try-on-model
REPLICATE_MODEL_VERSION=v1.0.0

# Storage
STORAGE_TYPE=s3  # or 'local'
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
AWS_S3_BUCKET=digicloset-tryon
AWS_REGION=us-east-1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_BACKEND_URL=redis://localhost:6379/1
CELERY_TASK_TIMEOUT=600
CELERY_TASK_MAX_RETRIES=3

# Rate Limiting
RATE_LIMIT_TRYONS_PER_MINUTE=10

# Inference Service
INFERENCE_SERVICE_URL=http://inference-service:8002
INFERENCE_SERVICE_TIMEOUT=10

# Database
DATABASE_URL=postgresql://user:password@localhost/digicloset

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
```

### Step 2: Database Setup

```bash
# Create database and run migrations
cd /packages/database
prisma migrate dev --name "add-tryon-schema"
prisma generate
```

### Step 3: Install Dependencies

```bash
# Shopify Backend
cd /apps/shopify-app/backend
pip install -r requirements.txt

# Inference Service
cd /services/inference-service
pip install httpx replicate-sdk

# Queue Worker
pip install celery redis
```

### Step 4: Update FastAPI App

```python
# /apps/shopify-app/backend/main.py
from fastapi import FastAPI
from routes import tryon
from middleware.tryon_errors import setup_error_handlers

app = FastAPI()

# Setup error handlers
setup_error_handlers(app)

# Include try-on routes
app.include_router(tryon.router)
```

### Step 5: Start Services

```bash
# Terminal 1: Shopify Backend
cd /apps/shopify-app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Inference Service
cd /services/inference-service
uvicorn inference_routes:app --host 0.0.0.0 --port 8002 --reload

# Terminal 3: Celery Worker
cd /services/queue-worker
celery -A tryon_tasks worker --loglevel=info

# Terminal 4: Celery Beat (for scheduled tasks)
celery -A tryon_tasks beat --loglevel=info

# Terminal 5: Redis
redis-server
```

---

## Deployment

### Docker Deployment

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  shopify-backend:
    build:
      context: ./apps/shopify-app/backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/digicloset
      - CELERY_BROKER_URL=redis://redis:6379/0
      - REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}
      - STORAGE_TYPE=s3
    depends_on:
      - postgres
      - redis

  inference-service:
    build:
      context: ./services/inference-service
      dockerfile: Dockerfile
    ports:
      - "8002:8002"
    environment:
      - REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}
      - STORAGE_TYPE=s3

  queue-worker:
    build:
      context: ./services/queue-worker
      dockerfile: Dockerfile
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/digicloset
      - REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}
    depends_on:
      - redis
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=digicloset
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

---

## Configuration

### Rate Limiting

Configure per-shop rate limiting in `middleware/tryon_errors.py`:

```python
# Default: 10 requests per minute per shop
RATE_LIMIT_TRYONS_PER_MINUTE = 10

# Implement with Redis
redis.incr(f"tryon_limit:{shop_id}")
redis.expire(f"tryon_limit:{shop_id}", 60)
```

### Image Validation

Configure in `tryon_service.py`:

```python
# Max image size: 10 MB
MAX_IMAGE_SIZE_MB = 10

# Acceptable formats
VALID_FORMATS = ["image/jpeg", "image/png", "image/webp"]

# Min/max dimensions
MIN_WIDTH = 256
MAX_WIDTH = 4096
MIN_HEIGHT = 256
MAX_HEIGHT = 4096
```

### Replicate API

Configure in `replicate_client.py`:

```python
# Polling timeout (seconds)
DEFAULT_TIMEOUT = 300

# Polling interval
POLL_INTERVAL = 2

# Max retries on network errors
MAX_RETRIES = 3
```

---

## Monitoring & Logging

### Structured Logging

All operations use structured logging via `middleware/tryon_errors.py`:

```python
TryOnLogger.log_generation_started(
    tryon_id="tryon_123",
    shop_id="shop_456",
    category="upper_body",
    request_id="req_789"
)

# Output:
# {
#   "timestamp": "2025-03-11T10:30:45Z",
#   "event": "generation_start",
#   "tryon_id": "tryon_123",
#   "shop_id": "shop_456",
#   "category": "upper_body",
#   "request_id": "req_789"
# }
```

### Metrics to Monitor

```
# Generation Metrics
- Avg processing time per generation
- Success rate (completed / total)
- Failure rate by error type

# Performance Metrics
- API response times
- Queue depth
- Worker throughput

# Business Metrics
- Daily active shops
- Try-ons per day
- Average credits used
- Revenue impact
```

### Celery Monitoring

```bash
# Install Flower
pip install flower

# Start Flower
celery -A tryon_tasks flower --port=5555

# Access at: http://localhost:5555
```

---

## Troubleshooting

### Issue: "Timeout waiting for prediction"

**Cause:** Generation taking longer than configured timeout

**Solution:**
```python
# Increase timeout in inference service
await client.generate_tryon_image(
    user_image_url="...",
    garment_image_url="...",
    timeout=600  # 10 minutes
)
```

### Issue: "Rate limit exceeded from Replicate"

**Cause:** Too many concurrent requests to Replicate API

**Solution:**
```python
# Add exponential backoff in replicate_client.py
await asyncio.sleep(2 ** retry_count)  # 2, 4, 8, 16 seconds

# Or: Implement request queue
task.apply_async(countdown=30)  # Delay execution
```

### Issue: "Storage failed, no fallback available"

**Cause:** S3 unavailable and local storage full

**Solution:**
```python
# Check S3 configuration
aws s3 ls s3://digicloset-tryon/

# Check local storage
df -h /tmp/digicloset-storage/

# Configure fallback
STORAGE_TYPE=local  # Use local as primary
```

### Issue: "Database connection pool exhausted"

**Cause:** Too many concurrent database queries

**Solution:**
```python
# Increase pool size in database config
DATABASE_URL=postgresql://user:pass@host/db?pool_size=20&max_overflow=40
```

---

## API Reference

### POST /api/v1/try-on/generate

Initiate a virtual try-on generation.

**Request:**
```json
{
  "user_image_url": "https://example.com/user.jpg",
  "garment_image_url": "https://example.com/garment.jpg",
  "product_id": "prod_123",
  "category": "upper_body"
}
```

**Response (202 Accepted):**
```json
{
  "id": "tryon_abc123",
  "status": "pending",
  "message": "Try-on generation started",
  "created_at": "2025-03-11T10:30:45Z"
}
```

**Errors:**
- `422 Unprocessable Entity` - Invalid input
- `402 Payment Required` - Insufficient credits
- `429 Too Many Requests` - Rate limited
- `500 Internal Server Error` - Unexpected error

---

### GET /api/v1/try-on/{tryon_id}

Check status of a try-on generation.

**Response (200 OK):**
```json
{
  "id": "tryon_abc123",
  "status": "completed",
  "image_url": "https://storage.example.com/result.jpg",
  "processing_time": 12.5,
  "credits_used": 1,
  "created_at": "2025-03-11T10:30:45Z"
}
```

**Status values:** `pending`, `processing`, `completed`, `failed`

---

### GET /api/v1/try-on/credits/check

Check if shop has credits available.

**Response (200 OK):**
```json
{
  "has_credits": true,
  "credits_remaining": 50,
  "message": "50 credits remaining this month"
}
```

---

### Full API Documentation

See OpenAPI specs at:
- Shopify Backend: `http://localhost:8000/docs`
- Inference Service: `http://localhost:8002/docs`

---

## Next Steps

1. **Customize UI** - Modify styles in `tryon-widget.js`
2. **Add Analytics** - Track user interactions and conversions
3. **Implement Webhooks** - Notify external systems of completion
4. **Setup Alerts** - Monitor for errors and performance issues
5. **A/B Testing** - Test widget placement and messaging
6. **Performance Tuning** - Optimize polling, image sizes, timeouts

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/digicloset/app/issues
- Documentation: https://docs.digicloset.app
- Email: support@digicloset.app
