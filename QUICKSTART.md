# Quick Reference: DigiCloset Monorepo

## 🚀 Get Started in 2 Minutes

```bash
# 1. Clone and setup
git clone <repo-url> && cd digicloset
cp .env.example .env

# 2. Start everything
docker-compose -f docker-compose.dev.yml up

# 3. Done! Access at:
# - Shopify App: http://localhost:8000
# - AI Service: http://localhost:8001
# - Inference Service: http://localhost:8002
# - API Docs: http://localhost:8000/docs
```

---

## 📁 Project Structure at a Glance

```
/apps/shopify-app          ← Main Shopify application
/services/ai-service       ← Recommendation engine
/services/inference-service ← Virtual try-on
/services/queue-worker     ← Background jobs
/packages/shared           ← Shared utilities & config
/packages/database         ← Prisma ORM schema
/infra/docker              ← Service Dockerfiles
```

---

## 🔧 Common Tasks

### Running Specific Service

```bash
# Option 1: Start just one service with Docker
docker-compose -f docker-compose.dev.yml up shopify-app

# Option 2: Run directly with Python
cd apps/shopify-app/backend
uvicorn main:app --reload
```

### Updating Configuration

```bash
# Edit .env file
# Changes apply to all services automatically
# (or restart services to pick up changes)
```

### Database Migrations

```bash
cd packages/database
npx prisma generate          # Generate client
npx prisma migrate deploy    # Run migrations
npx prisma studio          # Browse database
```

### Adding New Code to Shared

```bash
# 1. Add to /packages/shared/
# 2. Import in services
from packages.shared.config import config
from packages.shared.logging import get_logger
```

### Running Tests

```bash
pytest                      # All tests
pytest apps/shopify-app/backend/tests
pytest --cov               # With coverage
```

### Building Docker Images

```bash
docker build -f infra/docker/Dockerfile.shopify-app \
  -t digicloset-shopify-app .

# For all services, run once per service
```

---

## 📚 Important Files & Locations

| What | Where |
|------|-------|
| Configuration | `.env` and `.env.example` |
| Main README | `README.md` |
| Architecture guide | `ARCHITECTURE.md` |
| Refactoring details | `REFACTORING_GUIDE.md` |
| Deployment guide | `DEPLOYMENT.md` |
| Database schema | `packages/database/schema.prisma` |
| Shared config | `packages/shared/config.py` |
| Shared logging | `packages/shared/logging.py` |
| Docker Compose | `docker-compose.dev.yml` |
| Service Dockerfiles | `infra/docker/Dockerfile.*` |

---

## 🌐 API Endpoints

### Shopify App (Port 8000)
- `POST /api/v1/analyze` - Analyze product
- `GET /api/v1/products` - List products
- `GET /api/v1/health` - Health check
- `GET /docs` - API documentation

### AI Service (Port 8001)
- `POST /api/v1/embeddings` - Generate embeddings
- `POST /api/v1/search` - Search products
- `GET /health` - Health check

### Inference Service (Port 8002)
- `POST /api/v1/tryon` - Virtual try-on
- `GET /health` - Health check

---

## 🔐 Security Setup

```bash
# Create production config
cp .env.example .env.prod

# Update critical values
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=$(openssl rand -hex 32)
SHOPIFY_API_KEY=<your-key>
SHOPIFY_API_SECRET=<your-secret>
DATABASE_URL=<production-db>
```

---

## 📊 Monitoring & Debugging

```bash
# View logs from all services
docker-compose -f docker-compose.dev.yml logs -f

# View logs from specific service
docker-compose -f docker-compose.dev.yml logs -f shopify-app

# Check Redis
redis-cli -u $REDIS_URL ping

# Check database
psql $DATABASE_URL -c "SELECT 1"

# Test AI service
curl http://localhost:8001/health
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Port already in use | Change port in `.env` or Docker Compose |
| Database connection error | Ensure PostgreSQL is running, check DATABASE_URL |
| Redis connection error | Ensure Redis is running, check REDIS_URL |
| Module not found error | Ensure PYTHONPATH includes monorepo root |
| Docker build fails | Run `docker-compose build --no-cache` |

---

## 📖 Documentation Links

- **Architecture Overview**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Refactoring Guide**: [REFACTORING_GUIDE.md](./REFACTORING_GUIDE.md)
- **Production Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Refactoring Complete**: [REFACTORING_COMPLETE.md](./REFACTORING_COMPLETE.md)

---

## 🎯 Key Concepts

### Monorepo vs Microservices
✅ Single repo, multiple independent services
- Easy local development
- Shared code in `/packages/shared`
- Services communicate via HTTP/Redis

### Configuration Management
✅ Centralized in `packages/shared/config.py`
- Load from `.env` file
- Validated on startup
- Accessible from all services

### Logging
✅ Structured JSON logging
- Consistent format across services
- Request ID tracking
- Easy log aggregation

### Database
✅ Prisma ORM
- Type-safe queries
- Auto-generated migrations
- Models in `packages/database/schema.prisma`

---

## 🚀 Production Deployment

```bash
# Step 1: Build images
docker build -f infra/docker/Dockerfile.shopify-app -t digicloset-app .

# Step 2: Push to registry
docker push digicloset-app

# Step 3: Deploy to Kubernetes
kubectl apply -f infra/k8s/

# Or Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for full guide.

---

## 💡 Tips & Tricks

```bash
# Hot reload all services
docker-compose -f docker-compose.dev.yml up --build

# View real-time metrics
docker stats

# Check Prisma database
cd packages/database && npx prisma studio

# Run specific test file
pytest apps/shopify-app/backend/tests/test_api.py::test_analyze

# Format code
black apps/shopify-app/backend
ruff check --fix apps/shopify-app/backend
```

---

## 🤝 Contributing

1. Follow monorepo structure
2. Add shared code to `/packages/shared`
3. Use absolute imports from monorepo root
4. Write tests for new features
5. Document API changes in `/docs/API.md`

Example PR workflow:
```bash
git checkout -b feature/new-feature
# Make changes...
git add .
git commit -m "feat: Add new feature"
git push origin feature/new-feature
# Create PR and pass tests
```

---

## ❓ Questions?

- **Architecture**: See [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Setup issues**: See [REFACTORING_GUIDE.md](./REFACTORING_GUIDE.md)
- **Production**: See [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Summary**: See [REFACTORING_COMPLETE.md](./REFACTORING_COMPLETE.md)

---

**Last Updated:** March 11, 2026
**Version:** 2.0 (Production-Ready Monorepo)
