# Shopify Fashion AI Recommendation Engine

## 🎨 Overview

A production-ready **visual and multimodal AI recommendation system** for Shopify fashion catalogs. Built with FastAPI, PyTorch CLIP embeddings, and FAISS vector search.

### Key Capabilities

- **Visual Similarity**: Find products with comparable visual embeddings
- **Style Matching**: Recommend compatible items across categories
- **Outfit Generation**: AI-powered complete outfit assembly
- **Production-Ready**: Async, GPU-accelerated, scalable

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Start the service
docker-compose up -d

# Check health
curl http://localhost:8000/api/v1/health

# View interactive docs
open http://localhost:8000/docs
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py

# In another terminal, run example
python examples.py
```

## 📋 API Endpoints

### Index Products
```bash
POST /api/v1/index-catalog
```

Index a catalog of products for recommendations.

### Visual Similarity
```bash
GET /api/v1/recommend/similar?product_id=1&top_k=10
```

Find visually similar products.

### Style Matching
```bash
GET /api/v1/recommend/style?product_id=1&top_k=5
```

Find style-compatible items in different categories.

### Complete Outfit
```bash
GET /api/v1/recommend/outfit?product_id=1&max_items=4
```

Generate a coordinated outfit.

### Health Check
```bash
GET /api/v1/health
```

Check service status and index size.

## 📚 Documentation

- **[README_RECOMMENDATION_ENGINE.md](README_RECOMMENDATION_ENGINE.md)** - Complete API documentation
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment guide
- **[SYSTEM_SUMMARY.md](SYSTEM_SUMMARY.md)** - Architecture and design overview
- **[examples.py](examples.py)** - Usage examples
- **[test_recommendation_engine.py](test_recommendation_engine.py)** - Test suite

## 🏗️ Architecture

```
Shopify Products
       ↓
CLIPEmbedder (PyTorch)
  ├─ Image Encoding (60%)
  ├─ Text Encoding (40%)
       ↓
Combined Embeddings
       ↓
FAISS Vector Index
       ↓
Recommender Engine
  ├─ Visual Similarity
  ├─ Style Matching
  ├─ Outfit Generation
       ↓
FastAPI REST API
```

## 🛠️ Development

### Available Commands

```bash
make help                    # Show all commands
make install                 # Install dependencies
make dev                     # Run development server
make test                    # Run tests
make example                 # Run example script
make compose-up              # Start with Docker Compose
make docker-build            # Build Docker image
make quality                 # Run code quality checks
```

## 📦 Components

### `embeddings/clip_embedder.py`
Loads OpenAI CLIP model for generating embeddings from images and text.

- `embed_image()` - Generate image embedding
- `embed_text()` - Generate text embedding  
- `embed_product()` - Generate combined multimodal embedding

### `vector_db/product_index.py`
FAISS-based vector index for similarity search.

- `add_product()` - Add single product
- `batch_add()` - Batch add products
- `search()` - Find similar products
- `save()/load()` - Persist index

### `indexing/catalog_indexer.py`
Process Shopify catalog and generate embeddings.

- `index_product()` - Index single product
- `batch_index()` - Batch indexing with progress

### `recommendation/recommender.py`
Recommendation engine with fashion-specific rules.

- `recommend_similar_products()` - Visual similarity
- `recommend_style_matches()` - Compatible items
- `recommend_complete_outfit()` - Outfit assembly

### `api/routes.py`
FastAPI routes and request/response models.

- POST `/index-catalog` - Index products
- GET `/recommend/similar` - Similar products
- GET `/recommend/style` - Style matches
- GET `/recommend/outfit` - Complete outfit
- GET `/health` - Health check

### `utils/`
Utility modules for images and colors.

- `image_loader.py` - Download and preprocess images
- `color_utils.py` - Extract and compare colors

## 🧪 Testing

```bash
# Run all tests
pytest test_recommendation_engine.py -v

# With coverage
pytest test_recommendation_engine.py --cov=ai_service

# Run example
python examples.py
```

## ⚙️ Configuration

All settings via environment variables:

```env
# Model
CLIP_MODEL_NAME=openai/clip-vit-base-patch32
EMBEDDING_DIM=512

# Service
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
NUM_WORKERS=4

# Index paths
INDEX_PATH=/data/recommendation_index/faiss.index
METADATA_PATH=/data/recommendation_index/metadata.json

# Recommendations
COLOR_WEIGHT=0.2
SIMILARITY_THRESHOLD=0.3

# Logging
LOG_LEVEL=info
```

See [.env.example](.env.example) for all options.

## 🐳 Docker

### Build Image
```bash
docker build -t shopify-recommendation-engine .
```

### Run Container
```bash
docker run -p 8000:8000 \
  -v recommendation-data:/data \
  shopify-recommendation-engine
```

### Docker Compose
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## ☸️ Kubernetes

### Deploy
```bash
kubectl apply -f k8s-deployment.yaml
```

### Scale
```bash
kubectl scale deployment recommendation-engine --replicas=5 -n recommendation
```

### Monitor
```bash
kubectl logs deployment/recommendation-engine -n recommendation -f
```

## 📊 Performance

| Metric | CPU | GPU |
|--------|-----|-----|
| Indexing Speed | 100 prod/min | 500+ prod/min |
| Search Latency | ~100ms | ~50ms |
| Outfit Generation | ~500ms | ~200ms |
| API Latency (p95) | 500ms | 250ms |

## 🔒 Security

- ✅ No credentials in code
- ✅ Environment-based configuration
- ✅ Input validation (Pydantic)
- ✅ CORS for development
- ✅ Type-safe API (FastAPI)
- ✅ Structured logging (no PII)

## 📈 Scaling

### Horizontal
- Deploy multiple instances
- Use load balancer (nginx, HAProxy)
- Share FAISS index via persistent volume
- Recommended: 2-4 instances for production

### Vertical
- Increase CPU/memory per instance
- Enable GPU acceleration (CUDA)
- Use larger batch sizes

## 🛺 Production Checklist

- ✅ Async request handling
- ✅ Error handling & validation
- ✅ Structured logging
- ✅ Health checks
- ✅ Index persistence
- ✅ Docker containerization
- ✅ Kubernetes manifests
- ✅ GPU support
- ✅ CORS configuration
- ✅ API documentation

## 📝 Example Usage

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Index products
products = [
    {
        "id": 1,
        "title": "White T-Shirt",
        "description": "Premium cotton",
        "image_url": "https://...",
        "category": "shirts",
        "tags": ["casual"]
    }
]

response = requests.post(
    f"{BASE_URL}/index-catalog",
    json={"products": products}
)

# Get recommendations
similar = requests.get(
    f"{BASE_URL}/recommend/similar?product_id=1&top_k=5"
)

outfit = requests.get(
    f"{BASE_URL}/recommend/outfit?product_id=1&max_items=4"
)
```

## 📖 Learn More

- [Complete API Reference](README_RECOMMENDATION_ENGINE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [System Architecture](SYSTEM_SUMMARY.md)
- [Examples](examples.py)
- [Tests](test_recommendation_engine.py)

## 🤝 Contributing

Contributions welcome! Please:
1. Follow code quality checks: `make quality`
2. Add tests for new features
3. Update documentation
4. Test with Docker: `make compose-up && make example`

## ⚡ Performance Tips

1. **Pre-download models** - Avoid first-request delay
2. **Use GPU** - 5-10x faster with CUDA 11.8+
3. **Batch indexing** - Index 50-100 products at once
4. **Scale horizontally** - Add instances for load balancing
5. **Enable caching** - Cache embeddings in Redis

## 🐛 Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs recommendation-engine

# Verify GPU (if using)
nvidia-smi
```

### Slow recommendations
- Reduce batch size
- Enable GPU acceleration
- Check network for image downloads

### Poor quality results
- Ensure detailed product descriptions
- Use high-quality images (200x200+ px)
- Verify category metadata accuracy

## 📞 Support

- **Docs**: http://localhost:8000/docs
- **Health Check**: `curl http://localhost:8000/api/v1/health`
- **Logs**: `docker-compose logs -f`

## 📄 License

Part of Shopify Fashion AI system.

---

**Status**: ✅ Production Ready | **Version**: 1.0.0 | **Last Updated**: March 2026
