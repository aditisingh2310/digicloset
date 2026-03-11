# Production Deployment Guide

This guide covers deploying DigiCloset to production on Kubernetes, AWS ECS, or other container platforms.

## Pre-Deployment Checklist

### 1. Environment Configuration

```bash
# Create production .env file
cp .env.example .env.prod

# Update critical values
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=$(openssl rand -hex 32)
SHOPIFY_API_KEY=<prod-key>
SHOPIFY_API_SECRET=<prod-secret>
DATABASE_URL=postgresql://user:password@prod-postgres:5432/digicloset
REDIS_URL=redis://prod-redis:6379/0
ALLOWED_ORIGINS=https://yourdomain.com
```

### 2. Database Setup

```bash
# Use managed PostgreSQL service (AWS RDS, Azure Database, etc.)
# Ensure database is created and accessible
psql $DATABASE_URL -c "CREATE DATABASE digicloset;" 2>/dev/null

# Run migrations
cd packages/database
npx prisma generate
npx prisma migrate deploy --preview-feature
```

### 3. Storage Configuration

**Option A: Local Storage (small deployments)**
```bash
LOCAL_STORAGE_PATH=/mnt/storage  # Persistent volume
STORAGE_TYPE=local
```

**Option B: Amazon S3 (recommended)**
```bash
STORAGE_TYPE=s3
S3_BUCKET=digicloset-prod
S3_REGION=us-east-1
S3_ACCESS_KEY=<AWS_ACCESS_KEY>
S3_SECRET_KEY=<AWS_SECRET_KEY>
```

**Option C: Azure Blob Storage**
Configure via environment variables for Azure SDK

### 4. Redis Configuration

Use managed Redis service:
- **AWS ElastiCache** (recommended)
- **Azure Cache for Redis**
- **Google Cloud Memorystore**
- **Self-hosted with sentinel** (high availability)

### 5. Shopify Configuration

In Shopify Partner Dashboard:
1. Create Custom App
2. Set proper scopes:
   - `write_products`
   - `read_customers`
   - `write_orders`
   - `read_orders`
   - `write_order_notes`
3. Generate API Key and Secret
4. Set webhook endpoints:
   - Products: `https://yourdomain.com/api/v1/webhooks/shopify/products`
   - Orders: `https://yourdomain.com/api/v1/webhooks/shopify/orders`

### 6. External API Keys

```bash
REPLICATE_API_TOKEN=<replicate-token>      # For image generation
HUGGINGFACE_API_KEY=<hf-token>             # For embeddings (optional)
STRIPE_API_KEY=<stripe-key>                 # For billing
STRIPE_WEBHOOK_SECRET=<stripe-webhook-secret>
```

---

## Deployment Strategies

### Option 1: Kubernetes (Recommended for Scale)

**Prerequisites:**
- Kubernetes cluster (AWS EKS, GKE, AKE)
- `kubectl` configured
- Docker registry access (Docker Hub, AWS ECR, GCR)

**Deploy:**

```bash
# 1. Build and push images
docker build -f infra/docker/Dockerfile.shopify-app -t your-registry/digicloset-shopify-app:latest .
docker build -f infra/docker/Dockerfile.ai-service -t your-registry/digicloset-ai-service:latest .
docker build -f infra/docker/Dockerfile.inference-service -t your-registry/digicloset-inference-service:latest .
docker build -f infra/docker/Dockerfile.queue-worker -t your-registry/digicloset-queue-worker:latest .

docker push your-registry/digicloset-*:latest

# 2. Create namespace
kubectl create namespace digicloset

# 3. Create secrets
kubectl create secret generic digicloset-secrets \
  --from-env-file=.env.prod \
  -n digicloset

# 4. Deploy database and cache
kubectl apply -f infra/k8s/postgres-statefulset.yaml
kubectl apply -f infra/k8s/redis-deployment.yaml

# 5. Deploy services
kubectl apply -f infra/k8s/shopify-app-deployment.yaml
kubectl apply -f infra/k8s/ai-service-deployment.yaml
kubectl apply -f infra/k8s/inference-service-deployment.yaml
kubectl apply -f infra/k8s/queue-worker-deployment.yaml

# 6. Deploy ingress
kubectl apply -f infra/k8s/ingress.yaml

# 7. Check status
kubectl get pods -n digicloset
kubectl logs -f deployment/shopify-app -n digicloset
```

**Ingress Configuration (update domain):**

```yaml
# infra/k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: digicloset-ingress
  namespace: digicloset
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - yourdomain.com
      secretName: digicloset-tls
  rules:
    - host: yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: shopify-app
                port:
                  number: 8000
```

**Monitoring (add Prometheus):**

```bash
# Install Prometheus operator (Helm recommended)
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring

# Prometheus scrape config picks up service metrics automatically
```

### Option 2: AWS ECS (Elastic Container Service)

**Create task definitions:**

```bash
# Register task definitions
aws ecs register-task-definition \
  --cli-input-json file://infra/ecs/shopify-app-task-def.json

aws ecs register-task-definition \
  --cli-input-json file://infra/ecs/ai-service-task-def.json

# Create service
aws ecs create-service \
  --cluster digicloset \
  --service-name shopify-app \
  --task-definition shopify-app:1 \
  --desired-count 2 \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=shopify-app,containerPort=8000
```

### Option 3: Docker Compose (Small Deployments)

For small production deployments on single host:

```bash
# On production server
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale queue-worker=3
```

---

## Post-Deployment

### 1. Verify Services

```bash
# Health checks
curl https://yourdomain.com/health
curl https://yourdomain.com:8001/health
curl https://yourdomain.com:8002/health

# API documentation
open https://yourdomain.com/docs
```

### 2. Database Verification

```bash
# Connect to database
psql $DATABASE_URL

# Check tables
\dt
SELECT COUNT(*) FROM "Shop";
SELECT COUNT(*) FROM "AiResult";
```

### 3. Redis Verification

```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check memory usage
redis-cli -u $REDIS_URL INFO memory
```

### 4. Queue Worker Status

```bash
# Check RQ queue
rq info --interval 1

# View jobs
rq dashboard  # Access at http://localhost:9181
```

### 5. Logs

**Kubernetes:**
```bash
kubectl logs -f deployment/shopify-app -n digicloset
kubectl logs -f deployment/ai-service -n digicloset
kubectl logs -f deployment/queue-worker -n digicloset
```

**Docker:**
```bash
docker logs -f digicloset-shopify-app
docker logs -f digicloset-ai-service
```

### 6. Monitoring Setup

**Prometheus targets:**
- `http://shopify-app:8000/metrics`
- `http://ai-service:8001/metrics`
- `http://inference-service:8002/metrics`

**Useful alerts:**
- High error rate (>1%)
- High latency (p95 > 2s)
- Pod restart loops
- Database connection errors
- Redis connection errors

---

## Scaling

### Horizontal Scaling

**Shopify App (Stateless):**
```bash
# Kubernetes
kubectl scale deployment shopify-app --replicas=3 -n digicloset

# ECS
aws ecs update-service --cluster digicloset --service shopify-app --desired-count 3
```

**AI Service (Compute-intensive):**
```bash
# Fewer replicas, larger instances
kubectl scale deployment ai-service --replicas=2 -n digicloset
kubectl set resources deployment ai-service \
  --limits=cpu=4,memory=8Gi \
  --requests=cpu=2,memory=4Gi
```

**Queue Workers (Scalable):**
```bash
# Scale based on queue depth
kubectl scale deployment queue-worker --replicas=5 -n digicloset

# Or use autoscaling
kubectl autoscale deployment queue-worker --min=2 --max=10 --cpu-percent=70
```

### Database Scaling

- **Read replicas** for read-heavy workloads
- **Connection pooling** (PgBouncer)
- **Sharding** by shop_id if needed (>100GB data)

### Cache Layer

- **Redis cluster** for high traffic
- **Redis sentinel** for high availability
- **Connection pooling** in your app

---

## Security Hardening

### 1. Network Security

```bash
# Restrict API access
- Firewall rules for database (only from app services)
- VPC endpoint for Redis
- Security groups with minimal permissions
```

### 2. Secrets Management

```bash
# Use secret manager (not env files)
# AWS Secrets Manager
# Kubernetes Secrets with encryption at rest
# HashiCorp Vault

# Rotate keys regularly
- Shopify API secrets (annual)
- Database passwords (quarterly)
- JWT secrets (if using, annual)
```

### 3. Database Security

```sql
-- Create read-only user for analytics
CREATE USER analytics WITH PASSWORD 'strong-password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics;

-- Enable SSL
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = '/path/to/cert.pem';
```

### 4. API Security

```python
# Enable rate limiting in production
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Enable CORS restrictions
ALLOWED_ORIGINS=https://yourdomain.com

# Enable HTTPS only
REQUIRE_HTTPS=true
```

---

## Backup & Disaster Recovery

### Database Backups

```bash
# Automated daily backups (AWS RDS)
aws rds create-db-snapshot \
  --db-instance-identifier digicloset-prod \
  --db-snapshot-identifier digicloset-backup-$(date +%Y%m%d)

# Or using pg_dump
pg_dump $DATABASE_URL | gzip > backup-$(date +%Y%m%d).sql.gz
```

### Redis Snapshots

```bash
# Redis persistence (RDB + AOF)
redis-cli -u $REDIS_URL SAVE

# Copy to backup storage
aws s3 cp dump.rdb s3://digicloset-backups/
```

### Application Data

```bash
# Backup S3 objects
aws s3 sync s3://digicloset-prod s3://digicloset-backups/latest/prod --delete

# Retention policy: Keep 30 days minimum
```

---

## Performance Tuning

### Database

```sql
-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM "AiResult" WHERE shop = 'myshop';

-- Add indexes for common queries
CREATE INDEX idx_airesult_shop_created 
  ON "AiResult"(shop, "createdAt" DESC);
```

### Redis

```bash
# Monitor Redis performance
redis-cli -u $REDIS_URL --stat

# Tune memory policies
redis-cli -u $REDIS_URL CONFIG SET maxmemory-policy allkeys-lru
```

### Caching

```python
# Cache aggressively in production
REDIS_CACHE_TTL=86400  # 24 hours for recommendations
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
kubectl logs pod/shopify-app-xxx -n digicloset

# Check environment variables
kubectl exec pod/shopify-app-xxx -n digicloset -- env | grep DATABASE

# Check database connectivity
kubectl exec pod/shopify-app-xxx -n digicloset -- psql $DATABASE_URL -c "SELECT 1"
```

### High Latency

```bash
# Check database query performance
EXPLAIN ANALYZE select ...

# Check Redis latency
redis-cli -u $REDIS_URL LATENCY LATEST

# Check network latency
kubectl exec pod/shopify-app -n digicloset -- ping ai-service
```

### Memory Issues

```bash
# Check pod resource usage
kubectl top pods -n digicloset

# Increase resource limits
kubectl patch deployment shopify-app -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"shopify-app","resources":{"limits":{"memory":"1Gi"}}}]}}}}'
```

---

## Cost Optimization

1. **Right-size instances** - Monitor actual usage
2. **Use spot instances** - For non-critical workloads
3. **Reserved instances** - For predictable baseline load
4. **Autoscaling** - Scale down during off-peak hours
5. **CDN** - For static content (storefront widget)
6. **Managed services** - RDS vs self-hosted
7. **Image optimization** - Reduce storage costs

---

## Maintenance Schedule

- **Daily:** Monitor metrics and logs
- **Weekly:** Check backup completion
- **Monthly:** Security patches, dependency updates
- **Quarterly:** Performance review, cost optimization
- **Annually:** Database optimization, capacity planning

---

For further questions or issues, consult [ARCHITECTURE.md](../ARCHITECTURE.md) or the inline code documentation.
