# Deployment Guide

## Production Deployment - Shopify Fashion Recommendation Engine

This guide covers deploying the recommendation engine in production environments.

### Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [AWS Deployment](#aws-deployment)
7. [Performance Tuning](#performance-tuning)
8. [Monitoring & Operations](#monitoring--operations)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Service Components

```
┌─────────────────────────────────────┐
│   Shopify Catalog / API             │
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│  Recommendation Engine (FastAPI)    │
│  ├─ CLIPEmbedder (PyTorch)         │
│  ├─ ProductVectorIndex (FAISS)     │
│  ├─ Recommender Engine             │
│  └─ CatalogIndexer                 │
└─────────────────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│   Persistent Storage (Index Data)   │
│   └─ /data/recommendation_index/    │
└─────────────────────────────────────┘
```

### Scaling Strategy

- **Horizontal Scaling**: Multiple service instances behind load balancer
- **Index Sharing**: Single FAISS index shared across instances
- **Async Processing**: Background tasks for large catalog indexing
- **Caching**: Redis for embedding cache (optional)

---

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended)
- **CPU**: 4+ cores recommended
- **Memory**: 8GB minimum, 16GB+ recommended
- **Storage**: 10GB+ for FAISS index + models
- **Network**: Stable internet for downloading models

### Software Requirements

```bash
# Minimum versions
Python 3.9+
Docker 20.10+
Docker Compose 2.0+
Git 2.30+
```

### NVIDIA (for GPU acceleration)

```bash
# CUDA 11.8+
# cuDNN 8.0+
# nvidia-docker

# Check GPU
nvidia-smi
```

---

## Local Development

### 1. Clone and Setup

```bash
git clone <repository>
cd ai_service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
```

### 2. Run Development Server

```bash
# Start FastAPI development server (with auto-reload)
python main.py

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### 3. Test with Example Script

```bash
# In another terminal
python examples.py

# Expected output:
# ✓ Health Check passed
# ✓ Indexing Complete
# ✓ Found similar products
# ...
```

---

## Docker Deployment

### 1. Build Docker Image

```bash
# Build image
docker build -t shopify-recommendation-engine:latest .

# Build with specific tag
docker build -t shopify-recommendation-engine:v1.0.0 .

# Verify image
docker images | grep recommendation
```

### 2. Run Container

```bash
# Create directory for persistent data
mkdir -p /data/recommendation_index

# Run with default settings
docker run -d \
  --name recommendation-engine \
  -p 8000:8000 \
  -v /data/recommendation_index:/data/recommendation_index \
  shopify-recommendation-engine:latest

# Run with custom environment
docker run -d \
  --name recommendation-engine \
  -p 8000:8000 \
  -v /data/recommendation_index:/data/recommendation_index \
  -e CLIP_MODEL_NAME=openai/clip-vit-base-patch32 \
  -e NUM_WORKERS=4 \
  -e LOG_LEVEL=info \
  shopify-recommendation-engine:latest

# Check logs
docker logs -f recommendation-engine
```

### 3. Docker Compose

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove data
docker-compose down -v
```

---

## Kubernetes Deployment

### 1. Prepare Deployment

```bash
# Create namespace
kubectl create namespace recommendation

# Create ConfigMap for configuration
kubectl create configmap recommendation-config \
  --from-file=.env \
  -n recommendation

# Create persistent volume
kubectl apply -f k8s-deployment.yaml
```

### 2. Kubernetes Manifest

Create `k8s-deployment.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: recommendation-data
  namespace: recommendation
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: recommendation-engine
  namespace: recommendation
spec:
  replicas: 3
  selector:
    matchLabels:
      app: recommendation-engine
  template:
    metadata:
      labels:
        app: recommendation-engine
    spec:
      containers:
      - name: recommendation-service
        image: shopify-recommendation-engine:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: SERVICE_PORT
          value: "8000"
        - name: NUM_WORKERS
          value: "2"
        - name: LOG_LEVEL
          value: "info"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        volumeMounts:
        - name: index-data
          mountPath: /data
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 40
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 10
      volumes:
      - name: index-data
        persistentVolumeClaim:
          claimName: recommendation-data

---
apiVersion: v1
kind: Service
metadata:
  name: recommendation-engine
  namespace: recommendation
spec:
  type: LoadBalancer
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: recommendation-engine
```

### 3. Deploy

```bash
# Apply deployment
kubectl apply -f k8s-deployment.yaml

# Check deployment status
kubectl get deployments -n recommendation
kubectl get pods -n recommendation
kubectl describe service recommendation-engine -n recommendation

# View logs
kubectl logs -n recommendation deployment/recommendation-engine -f

# Scale replicas
kubectl scale deployment recommendation-engine -n recommendation --replicas=5

# Update image
kubectl set image deployment/recommendation-engine \
  recommendation-service=shopify-recommendation-engine:v1.1.0 \
  -n recommendation
```

---

## AWS Deployment

### 1. Using ECS (Elastic Container Service)

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name recommendation-cluster

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster recommendation-cluster \
  --service-name recommendation-service \
  --task-definition recommendation-task:1 \
  --desired-count 3
```

### 2. Using EKS (Elastic Kubernetes Service)

```bash
# Create EKS cluster
eksctl create cluster --name recommendation --region us-east-1

# Deploy application
kubectl apply -f k8s-deployment.yaml

# Update kubeconfig
aws eks update-kubeconfig \
  --region us-east-1 \
  --name recommendation
```

### 3. Using Lambda (for API endpoints)

For lighter workloads, consider AWS Lambda with API Gateway:

```bash
# Package application
zip -r lambda-package.zip ai_service/

# Create Lambda function
aws lambda create-function \
  --function-name recommendation-inference \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler main.handler \
  --zip-file fileb://lambda-package.zip
```

---

## Performance Tuning

### 1. Model Loading

```python
# Pre-download models to avoid first-run delays
from transformers import CLIPModel, CLIPProcessor

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
```

### 2. FAISS Index Optimization

```bash
# Use GPU FAISS for large catalogs
pip install faiss-gpu

# Or use optimized CPU version
pip install faiss-cpu
```

### 3. Worker Configuration

```bash
# Adjust based on CPU cores
# 4 cores: NUM_WORKERS=2
# 8 cores: NUM_WORKERS=4
# 16 cores: NUM_WORKERS=8

docker run -e NUM_WORKERS=4 ...
```

### 4. Caching Strategy

```python
# Redis caching (optional)
import redis

cache = redis.Redis(host='localhost', port=6379)

# Cache embeddings
cache.setex(
    f"embedding:{product_id}",
    3600,  # 1 hour TTL
    embedding.tobytes()
)
```

### 5. Batch Processing

```bash
# Index large catalogs in batches
# Recommended batch size: 32-256 based on memory

# Example: Index 100k products
# 100,000 / 64 = 1,562 batches
# ~15-20 minutes with GPU

curl -X POST http://localhost:8000/api/v1/index-catalog \
  -H "Content-Type: application/json" \
  -d '{
    "products": [/* 64 products */],
    "batch_size": 64
  }'
```

---

## Monitoring & Operations

### 1. Health Checks

```bash
# Simple health check
curl http://localhost:8000/api/v1/health

# Expected response
{
  "status": "healthy",
  "indexed_products": 10000,
  "model": "openai/clip-vit-base-patch32",
  "device": "cuda:0"
}
```

### 2. Prometheus Metrics

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'recommendation-engine'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 3. Logging

```bash
# View logs from container
docker logs recommendation-engine

# Export logs
docker logs recommendation-engine > app.log 2>&1

# With Kubernetes
kubectl logs deployment/recommendation-engine -n recommendation > app.log
```

### 4. Alerting

```yaml
# AlertManager rules
groups:
- name: recommendation-alerts
  rules:
  - alert: HighLatency
    expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
    for: 5m
  - alert: ServiceDown
    expr: up{job="recommendation-engine"} == 0
    for: 1m
```

---

## Troubleshooting

### Issue: Out of Memory

**Symptom**: Service crashes with OOM error

**Solution**:
```bash
# Reduce batch size
docker run -e MAX_BATCH_SIZE=128 ...

# Use CPU-only FAISS
pip uninstall faiss-gpu
pip install faiss-cpu

# Increase container memory limit
docker run -m 4g ...
```

### Issue: Slow Model Loading

**Symptom**: First request takes 30+ seconds

**Solution**:
```bash
# Pre-warm GPU
# Run dummy inference on startup

# Use smaller model
CLIP_MODEL_NAME=openai/clip-vit-base-patch16

# Or larger faster model
CLIP_MODEL_NAME=openai/clip-vit-large-patch14
```

### Issue: Poor Recommendation Quality

**Symptom**: Recommendations don't match user expectations

**Solution**:
1. Verify product descriptions are detailed
2. Ensure image quality (min 200x200px)
3. Check category metadata accuracy
4. Adjust weights: `COLOR_WEIGHT=0.3`, `SIMILARITY_THRESHOLD=0.4`

### Issue: High Latency

**Symptom**: API responses slow

**Solution**:
```bash
# Increase workers
NUM_WORKERS=8

# Use GPU
DEVICE=cuda

# Enable caching
ENABLE_CACHE=true
CACHE_TTL=3600

# Reduce k in searches
# Instead of top_k=100, use top_k=10
```

### Issue: Index Corruption

**Symptom**: Search returns no results or errors

**Solution**:
```bash
# Clear and rebuild index
rm -rf /data/recommendation_index/*

# Re-index catalog
curl -X POST http://localhost:8000/api/v1/index-catalog \
  -H "Content-Type: application/json" \
  -d '{"products": [...]}'
```

---

## Maintenance

### Regular Tasks

```bash
# 1. Monitor disk space
du -sh /data/recommendation_index

# 2. Backup index
tar -czf recommendation_index_backup.tar.gz /data/recommendation_index

# 3. Update models
pip install --upgrade transformers torch

# 4. Check logs for errors
tail -f /var/log/recommendation-engine.log

# 5. Performance monitoring
docker stats recommendation-engine
```

### Updates

```bash
# Update service
docker pull shopify-recommendation-engine:latest
docker-compose down
docker-compose up -d

# Blue-green deployment with Kubernetes
kubectl set image deployment/recommendation-engine \
  recommendation-service=shopify-recommendation-engine:v1.1.0 \
  --record -n recommendation
```

---

## Security Considerations

1. **Authentication**: Add API key or JWT authentication
2. **Network**: Use private networks, VPCs
3. **Data**: Encrypt data at rest and in transit
4. **Secrets**: Use environment variables with secrets manager
5. **Rate Limiting**: Implement per-user rate limiting
6. **Logging**: Ensure PII is not logged
7. **Access Control**: Use IAM roles and RBAC

---

## Support & Resources

- API Documentation: `http://localhost:8000/docs`
- GitHub Issues: [Repository issues]
- Logs: Check container/pod logs
- Metrics: Monitor via Prometheus/Grafana

---

**Last Updated**: 2024
**Version**: 1.0.0
