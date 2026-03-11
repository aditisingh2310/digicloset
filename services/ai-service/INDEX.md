# 📑 Project Index & Navigation Guide

## 📂 Directory Structure

```
ai_service/
├── Core Implementation
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── clip_embedder.py              ← CLIP model 
│   ├── vector_db/
│   │   ├── __init__.py
│   │   └── product_index.py              ← FAISS index
│   ├── indexing/
│   │   ├── __init__.py
│   │   └── catalog_indexer.py            ← Catalog processing
│   ├── recommendation/
│   │   ├── __init__.py
│   │   └── recommender.py                ← Recommendation engine
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                     ← FastAPI endpoints
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── image_loader.py               ← Image utilities
│   │   └── color_utils.py                ← Color utilities
│   └── main.py                           ← FastAPI application
│
├── Deployment & Configuration
│   ├── Dockerfile                        ← Production image
│   ├── docker-compose.yml                ← Local setup
│   ├── k8s-deployment.yaml               ← Kubernetes
│   ├── .env.example                      ← Configuration
│   ├── requirements.txt                  ← Dependencies
│   └── Makefile                          ← Development commands
│
├── Testing & Examples
│   ├── test_recommendation_engine.py     ← Tests
│   ├── examples.py                       ← Example usage
│   └── BUILD_VERIFICATION.txt            ← Build verification
│
└── Documentation
    ├── README.md                         ← Quick start
    ├── README_RECOMMENDATION_ENGINE.md   ← API reference
    ├── DEPLOYMENT_GUIDE.md               ← Production guide
    ├── SYSTEM_SUMMARY.md                 ← Architecture
    ├── BUILD_SUMMARY.md                  ← Build report
    └── INDEX.md                          ← This file
```

---

## 🗂️ File Guide

### Core Implementation Files

#### `embeddings/clip_embedder.py`
**Purpose**: CLIP model integration for multimodal embeddings
- `CLIPEmbedder` class: Loads and manages CLIP model
- Methods:
  - `embed_image()` - Generate 512-d embedding from image
  - `embed_text()` - Generate embedding from text
  - `embed_product()` - Combined multimodal embedding
- Features:
  - Automatic GPU/CPU detection
  - Normalized embeddings
  - Error handling with fallbacks

**Read this if**: You want to understand how embeddings are generated

#### `vector_db/product_index.py`
**Purpose**: FAISS-based vector storage for similarity search
- `ProductVectorIndex` class: Manages FAISS index
- Methods:
  - `add_product()` - Add single product
  - `batch_add()` - Batch add products
  - `search()` - Find similar products
  - `search_with_metadata()` - Search with product info
  - `save()/load()` - Persist index
- Features:
  - Normalized L2 distance (cosine similarity)
  - Metadata storage
  - Index persistence

**Read this if**: You want to understand vector search

#### `indexing/catalog_indexer.py`
**Purpose**: Process Shopify catalog and generate embeddings
- `CatalogIndexer` class: Manages indexing workflow
- Methods:
  - `index_product()` - Index single product
  - `batch_index()` - Batch processing
- Features:
  - Image download with retry
  - Text fallback if image fails
  - Error tracking
  - Progress reporting

**Read this if**: You want to understand catalog processing

#### `recommendation/recommender.py`
**Purpose**: Recommendation engine with outfit generation
- `Recommender` class: Generates recommendations
- Methods:
  - `recommend_similar_products()` - Visual similarity
  - `recommend_style_matches()` - Style compatibility
  - `recommend_complete_outfit()` - Outfit assembly
- Features:
  - Fashion compatibility rules (15 categories)
  - Color similarity scoring
  - Weighted compatibility scoring

**Read this if**: You want to understand recommendations

#### `api/routes.py`
**Purpose**: FastAPI endpoints for the REST API
- Functions:
  - `create_router()` - Create API router
  - Endpoints: /index-catalog, /recommend/*, /health
- Features:
  - Pydantic validation
  - Async request handling
  - Exception handling
  - OpenAPI documentation

**Read this if**: You want to understand the API

#### `utils/image_loader.py`
**Purpose**: Image downloading and preprocessing
- `ImageLoader` class: Manages image loading
- Functions:
  - `download_image()` - HTTP image download with retry
  - `load_from_url()` - Load from URL
  - `load_from_path()` - Load from file
  - `preprocess()` - Resize and normalize
- Features:
  - Automatic retry on failure
  - Aspect ratio preservation
  - RGB conversion

**Read this if**: You want to understand image processing

#### `utils/color_utils.py`
**Purpose**: Color analysis for outfit compatibility
- Functions:
  - `get_dominant_colors()` - Extract 5 dominant colors
  - `color_similarity()` - Compare color similarity
  - `rgb_to_hsv()` - Color space conversion
- Features:
  - K-means clustering (or quantization fallback)
  - HSV color space for perception
  - Weighted color comparison

**Read this if**: You want to understand color analysis

#### `main.py`
**Purpose**: FastAPI application and service lifecycle
- `lifespan()` - Manage service startup/shutdown
- Global variables: embedder, vector_index, recommender
- Features:
  - Model loading on startup
  - Index loading from disk
  - GPU cache clearing on shutdown
  - CORS configuration
  - Exception handling

**Read this if**: You want to understand service initialization

---

### Configuration Files

#### `Dockerfile`
**Purpose**: Production Docker image
- Multi-stage build (builder + runtime)
- Minimal final image
- Health checks
- Non-root user

**Use when**: Building production Docker image

#### `docker-compose.yml`
**Purpose**: Local development with Docker
- Single service definition
- Volume mounting
- Environment configuration

**Use when**: Developing locally with Docker

#### `k8s-deployment.yaml`
**Purpose**: Kubernetes deployment manifests
- Deployment, Service, PVC, ConfigMap
- HorizontalPodAutoscaler
- NetworkPolicy, PodDisruptionBudget

**Use when**: Deploying to Kubernetes

#### `.env.example`
**Purpose**: Environment configuration template
- Model settings
- Service configuration
- Index paths
- Recommendation parameters

**Use when**: Setting up configuration

#### `requirements.txt`
**Purpose**: Python dependencies
- FastAPI, Uvicorn
- PyTorch, Transformers
- FAISS, Pillow, NumPy
- Testing/development tools

**Use when**: Installing dependencies

#### `Makefile`
**Purpose**: Development and deployment automation
- 40+ commands
- Dev, test, Docker, production targets

**Use when**: Running common tasks

---

### Testing & Examples

#### `examples.py`
**Purpose**: Complete usage example
- `RecommendationEngineClient` class
- Sample Shopify product catalog
- Demonstrates all endpoints
- Performance metrics

**How to use**:
```bash
python examples.py
```

#### `test_recommendation_engine.py`
**Purpose**: Unit and integration tests
- Tests for each component
- Fixtures for setup
- Integration workflow test

**How to use**:
```bash
pytest test_recommendation_engine.py -v
```

---

### Documentation Files

#### `README.md`
**Start here for**: Quick start and overview
- Installation steps
- API endpoint overview
- Docker quickstart
- Common tasks

#### `README_RECOMMENDATION_ENGINE.md`
**Read for**: Complete API reference
- Detailed endpoint documentation
- Request/response examples
- Fashion compatibility rules
- Performance optimization
- Troubleshooting

#### `DEPLOYMENT_GUIDE.md`
**Read for**: Production deployment strategies
- Local development setup
- Docker deployment
- Kubernetes configuration
- AWS deployment options
- Performance tuning
- Monitoring and alerting

#### `SYSTEM_SUMMARY.md`
**Read for**: Architecture and design
- System overview
- Technology stack
- Performance characteristics
- Scaling strategies
- Security considerations
- Future enhancements

#### `BUILD_SUMMARY.md`
**Read for**: Build completion report
- File structure
- Features implemented
- Configuration options
- Testing guide
- Next steps

---

## 🔍 How to Find What You Need

### "I want to..."

#### Understand the system
1. Read: README.md (overview)
2. Read: SYSTEM_SUMMARY.md (architecture)
3. Review: main.py (entry point)

#### Use the API
1. Read: README.md (quick start)
2. Run: `make example`
3. Review: examples.py (code)
4. Check: http://localhost:8000/docs (interactive)

#### Deploy to production
1. Read: DEPLOYMENT_GUIDE.md
2. Choose: Docker or Kubernetes
3. Configure: .env.example
4. Deploy: `make deploy-docker` or `kubectl apply`

#### Add custom code
1. Review: recommender.py (for recommendation logic)
2. Review: api/routes.py (for new endpoints)
3. Run tests: `make test`
4. Check quality: `make quality`

#### Fix a problem
1. Read: DEPLOYMENT_GUIDE.md (Troubleshooting section)
2. Check: logs with `make logs`
3. Run: health check with `make check-health`
4. Review: test cases in test_recommendation_engine.py

#### Understand a component
1. Find in file list above
2. Read the docstring
3. Review the class/function
4. Check the tests
5. Try the example

---

## 📋 Common Commands

```bash
# Development
make install          # Install dependencies
make dev              # Run development server
make test             # Run tests
make example          # Run example

# Docker
make compose-up       # Start Docker Compose
make docker-build     # Build Docker image
docker-compose logs   # View service logs

# Production
make deploy-docker    # Deploy with Docker
kubectl apply         # Deploy to Kubernetes

# Utilities
make check-health     # Check service status
make quality          # Code quality checks
make reset            # Full reset (clear data)
```

---

## 🎯 Key Concepts

### Multimodal Embeddings
- Combines image and text representations
- Image: 60% weight (visual features)
- Text: 40% weight (semantic meaning)
- Result: 512-dimensional normalized vector

### Recommendation Types
1. **Visual Similarity**: Based on image embeddings
2. **Style Matching**: Using fashion compatibility rules
3. **Outfit Generation**: AI-powered outfit assembly

### Fashion Rules
- 15 product categories with compatibility mappings
- Example: "shirt" compatible with "pants", "jacket", "shoes"
- Used for intelligent outfit recommendations

### Compatibility Scoring
- Embedding similarity (40%)
- Color similarity (40%)
- Category compatibility (20%)
- Result: 0-1 score

---

## 🚀 Quick Path by Use Case

### Path 1: Quick Test (5 minutes)
```bash
docker-compose up -d
python examples.py
curl http://localhost:8000/api/v1/health
```

### Path 2: Local Development (15 minutes)
```bash
pip install -r requirements.txt
python main.py
# In another terminal:
python examples.py
```

### Path 3: Production Kubernetes
```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -n recommendation
```

### Path 4: AWS Deployment
Read DEPLOYMENT_GUIDE.md "AWS Deployment" section

### Path 5: Custom Integration
1. Review examples.py
2. Use RecommendationEngineClient as template
3. Implement your HTTP client
4. Call endpoints from your app

---

## 📞 Getting Help

**For API usage**: 
- Check http://localhost:8000/docs
- Review README_RECOMMENDATION_ENGINE.md
- Check examples.py

**For deployment**:
- Read DEPLOYMENT_GUIDE.md
- Check Makefile for commands
- Review docker-compose.yml

**For architecture**:
- Read SYSTEM_SUMMARY.md
- Review diagrams
- Check comments in code

**For troubleshooting**:
- Check DEPLOYMENT_GUIDE.md troubleshooting section
- Review logs: `make logs`
- Run health check: `make check-health`

---

**Last Updated**: March 9, 2026
**Version**: 1.0.0
