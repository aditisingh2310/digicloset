# Async Queue System Implementation Guide

## Overview

This document describes the complete async queue system for try-on generation, using:
- **Celery**: Distributed task queue
- **Redis**: Message broker and result backend
- **PostgreSQL**: Job state tracking and billing

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Frontend / Mobile Client                             │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓ POST /try-on/request
┌─────────────────────────────────────────────────────┐
│ Backend API (FastAPI)                               │
│ ├─ Validate billing limits                          │
│ ├─ Create job in database                           │
│ └─ Submit to Celery queue → Job ID returned immediately
└────────────────┬────────────────────────────────────┘
                 │
                 ↓ Async task
┌─────────────────────────────────────────────────────┐
│ Redis Queue                                         │
│ (pending job)                                       │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────┐
│ Celery Worker Pool                                  │
│ ├─ Download images                                  │
│ ├─ Call ML inference service                        │
│ ├─ Upload result to S3/GCS                          │
│ └─ Update database with result                      │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────┐
│ PostgreSQL                                          │
│ (job status: pending → processing → completed)      │
└─────────────────────────────────────────────────────┘

Frontend polls: GET /try-on/status/{job_id}
Response includes image_url when ready
```

## API Endpoints

### 1. Submit Try-On Request

**POST /try-on/request**

Request:
```json
{
    "user_image_url": "https://example.com/user.jpg",
    "garment_image_url": "https://example.com/garment.jpg",
    "product_id": "PROD_12345",
    "category": "upper_body",
    "shop_id": 12345
}
```

Response (immediate):
```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "message": "Try-on generation queued. 49 generations remaining this month."
}
```

**Status Codes:**
- `200 OK`: Job submitted successfully
- `400 Bad Request`: Missing required fields or invalid input
- `429 Too Many Requests`: Billing limit exceeded
- `500 Internal Server Error`: Server error

### 2. Poll Job Status

**GET /try-on/status/{job_id}**

Response (while pending):
```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "image_url": null,
    "generation_time": null,
    "error": null,
    "created_at": "2024-01-15T10:30:00Z"
}
```

Response (when completed):
```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "image_url": "https://s3.amazonaws.com/digicloset-tryon-results/shops/12345/tryon/<job_id>.png",
    "generation_time": 3500,
    "error": null,
    "created_at": "2024-01-15T10:30:00Z"
}
```

Response (if failed):
```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "image_url": null,
    "generation_time": null,
    "error": "Failed to download user image",
    "created_at": "2024-01-15T10:30:00Z"
}
```

### 3. Get History

**GET /try-on/history?shop_id=12345&limit=20&offset=0**

Response:
```json
{
    "jobs": [
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "completed",
            "product_id": "PROD_12345",
            "image_url": "https://...",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:33:30Z"
        }
    ],
    "total": 145,
    "limit": 20,
    "offset": 0
}
```

## Database Schema

### tryon_job Table
```sql
CREATE TABLE tryon_job (
    id UUID PRIMARY KEY,
    shop_id INTEGER NOT NULL,
    status VARCHAR(20),  -- pending, processing, completed, failed
    user_image_url TEXT,
    garment_image_url TEXT,
    product_id VARCHAR(255),
    category VARCHAR(100),
    result_image_url TEXT,
    generation_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### store_plans Table (Billing)
```sql
CREATE TABLE store_plans (
    shop_id INTEGER PRIMARY KEY,
    plan_name VARCHAR(100),        -- free, starter, pro
    generation_limit INTEGER,      -- Monthly budget
    used_generations INTEGER,      -- Current usage
    cycle_start_date DATE,
    cycle_end_date DATE
);
```

## Deployment

### Local Development

1. **Start Redis**:
```bash
docker run -d -p 6379:6379 redis:latest
```

2. **Start Celery Worker**:
```bash
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
celery -A queue_worker.app worker --loglevel=INFO
```

3. **Start Celery Beat (for scheduled tasks)**:
```bash
celery -A queue_worker.app beat --loglevel=INFO
```

4. **Start Flower Monitoring**:
```bash
celery -A queue_worker.app flower
# Access at http://localhost:5555
```

5. **Start Backend API**:
```bash
cd services/backend-api
uvicorn app.main:app --reload
```

### Docker Compose

```bash
docker-compose -f docker-compose.celery.yml up -d
```

This starts:
- Redis on port 6379
- Celery worker with concurrency=4
- Celery beat for scheduled tasks
- Flower monitoring on port 5555
- Inference service (model hosting)

### Kubernetes (Production)

#### 1. Create ConfigMap for configuration:
```bash
kubectl create configmap celery-config \
  --from-literal=CELERY_BROKER_URL=redis://redis:6379/0 \
  --from-literal=DATABASE_URL=postgresql://... \
  --from-literal=ENVIRONMENT=production
```

#### 2. Deploy Redis:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  selector:
    app: redis
  ports:
  - port: 6379
  clusterIP: None
```

#### 3. Deploy Celery Worker:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: worker
        image: digicloset:celery-worker-latest
        env:
        - name: CELERY_BROKER_URL
          valueFrom:
            configMapKeyRef:
              name: celery-config
              key: CELERY_BROKER_URL
        resources:
          requests:
            cpu: 1000m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          exec:
            command:
            - celery
            - -A
            - queue_worker.app
            - inspect
            - active
          initialDelaySeconds: 10
          periodSeconds: 30
```

#### 4. Deploy Celery Beat:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-beat
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: beat
        image: digicloset:celery-worker-latest
        command:
        - celery
        - -A
        - queue_worker.app
        - beat
        env:
        - name: CELERY_BROKER_URL
          valueFrom:
            configMapKeyRef:
              name: celery-config
              key: CELERY_BROKER_URL
```

## Configuration

### Environment Variables

```bash
# Broker & Backend
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Database
DATABASE_URL=postgresql://user:pass@localhost/digicloset

# Inference Service
INFERENCE_SERVICE_URL=http://inference-service:8000

# Storage (S3, GCS, or local)
STORAGE_TYPE=s3  # s3, gcs, local
S3_BUCKET=digicloset-tryon-results
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Worker Configuration
CELERY_WORKER_CONCURRENCY=4
CELERY_LOG_LEVEL=INFO

# Monitoring
FLOWER_PORT=5555
SENTRY_DSN=...  # Optional error tracking

# Environment
ENVIRONMENT=production  # development, staging, production
```

### Scaling

To handle more concurrent jobs:

1. **Increase Worker Concurrency**:
```bash
celery -A queue_worker.app worker --concurrency=8
```

2. **Add More Worker Instances**:
```bash
# Terminal 1
celery -A queue_worker.app worker --concurrency=4

# Terminal 2
celery -A queue_worker.app worker --concurrency=4
```

3. **Use Multiple Queues**:
- `tryon` queue: Try-on generation (high priority)
- `default` queue: Cleanup and maintenance tasks

Monitor worker distribution in Flower at http://localhost:5555

## Monitoring & Debugging

### Flower Web UI

Access at http://localhost:5555 to see:
- Active tasks and workers
- Task execution times
- Success/failure rates
- Queue depth

### Celery Inspect Command

```bash
# View active tasks
celery -A queue_worker.app inspect active

# View registered tasks
celery -A queue_worker.app inspect registered

# View worker stats
celery -A queue_worker.app inspect stats

# View active queue config
celery -A queue_worker.app inspect active_queues
```

### Check Queue Depth

```bash
# Redis CLI
redis-cli
LLEN celery  # Default queue
LLEN tryon   # Try-on priority queue
```

### View Task Logs

```bash
# Follow worker logs
docker logs -f digicloset-celery-worker-tryon

# Or with docker-compose
docker-compose -f docker-compose.celery.yml logs -f celery-worker-tryon
```

### Monitor Performance

Query the database for metrics:

```sql
-- Jobs completed today
SELECT COUNT(*), AVG(generation_time_ms) as avg_time_ms
FROM tryon_job
WHERE status = 'completed'
  AND DATE(completed_at) = CURRENT_DATE;

-- Failed jobs
SELECT COUNT(*), error_message
FROM tryon_job
WHERE status = 'failed'
GROUP BY error_message;

-- Slowest jobs
SELECT id, generation_time_ms, created_at
FROM tryon_job
WHERE status = 'completed'
ORDER BY generation_time_ms DESC
LIMIT 10;
```

## Error Handling & Retries

### Retry Strategy

Default configuration:
- Max retries: 3
- Retry delay: 60 seconds (doubled each retry)
- Task timeout: 15 minutes

### Common Failures

**Image Download Failure**:
- Automatic retry with exponential backoff
- If all retries fail, job marked as failed

**Inference Service Timeout**:
- Task killed after 14 minutes (soft limit)
- Can be retried if configured in task decorator

**Storage Upload Failure**:
- Retry with backoff
- Job marked failed if all retries exhausted

## Performance Tuning

### Database Query Optimization

Indexes are already in place for:
- `shop_id` (common filter)
- `status` (job filtering)
- `created_at` (pagination)

### Redis Memory Management

```bash
# Set max memory policy
redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Worker Concurrency

Default: 4 workers per instance

Guidelines:
- **CPU-intensive (ML inference)**: 1-2 workers per CPU core
- **I/O-intensive (downloads/uploads)**: 8-16 workers per CPU core

### Prefetch Setting

Default: 4 tasks per worker

Lower values = better load distribution across workers
Higher values = fewer queue lookups

## Testing

### Unit Tests

```bash
pytest tests/test_tryon_tasks.py

# With coverage
pytest --cov=queue_worker tests/
```

### Integration Tests

```bash
# Test with real Redis
docker run -d -p 6379:6379 redis:latest
pytest tests/test_tryon_integration.py
```

### Load Testing

```bash
# Generate 100 test jobs
for i in {1..100}; do
    curl -X POST http://localhost:8000/try-on/request \
        -H "Content-Type: application/json" \
        -d '{
            "user_image_url": "https://example.com/user.jpg",
            "garment_image_url": "https://example.com/garment.jpg",
            "product_id": "'PROD_$i'",
            "shop_id": 12345
        }'
done
```

## Troubleshooting

### Workers Not Processing Tasks

1. Check Redis connection:
```bash
redis-cli ping
```

2. Check worker is registered:
```bash
celery -A queue_worker.app inspect registered
```

3. Check if tasks are stuck:
```bash
celery -A queue_worker.app inspect active
```

### High Memory Usage

1. Monitor worker memory:
```bash
docker stats digicloset-celery-worker-tryon
```

2. Lower concurrency:
```bash
# Instead of 8 workers, use 4
celery -A queue_worker.app worker --concurrency=4
```

3. Reduce prefetch:
```bash
celery -A queue_worker.app worker --prefetch-multiplier=2
```

### Job Stuck in Pending State

1. Check if worker is running:
```bash
celery -A queue_worker.app inspect active
```

2. Check Redis:
```bash
redis-cli LLEN celery
```

3. View task details:
```sql
SELECT * FROM tryon_job WHERE status = 'pending' AND created_at < NOW() - INTERVAL 5 minutes;
```

4. Reset stuck job:
```sql
UPDATE tryon_job SET status = 'failed' WHERE id = 'job-id';
```

## Migration from Synchronous to Async

If you have existing synchronous try-on generation:

1. Keep old endpoint working for backward compatibility
2. New code uses `/try-on/request` endpoint
3. Gradually migrate clients to poll `/try-on/status/{job_id}`
4. After migration period, deprecate old endpoint

## Future Improvements

1. **WebSocket Support**: Real-time job status updates instead of polling
2. **Job Prioritization**: Queue jobs by shop plan (pro plans get priority)
3. **Batch Processing**: Process multiple try-ons in parallel
4. **GPU Optimization**: Distribute GPU-intensive tasks to specialized workers
5. **Caching**: Cache common try-on combinations to avoid re-computation
6. **Analytics Dashboard**: Real-time metrics in Flower or custom dashboard

## Support & Debugging

For issues:
1. Check Flower UI: http://localhost:5555
2. Review worker logs: `docker logs celery-worker-*`
3. Query database for job status
4. Check Redis queue depth
5. Monitor system resources (CPU, memory, disk)

Contact: devops@digicloset.com
