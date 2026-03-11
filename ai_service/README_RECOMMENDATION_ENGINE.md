# Shopify Fashion AI Recommendation Engine

## Overview

A production-ready visual and multimodal AI recommendation engine for Shopify fashion stores. Generates product embeddings using OpenAI's CLIP model and performs intelligent recommendations using FAISS vector search.

### Key Features

- **Visual Similarity Search**: Find visually similar products using deep learning embeddings
- **Multimodal Embeddings**: Combines image and text embeddings for comprehensive product understanding
- **Style Matching**: Recommends items that complement product style across categories
- **Complete Outfit Generation**: AI-powered outfit assembly with compatibility scoring
- **Production-Ready**: Async FastAPI, GPU support, comprehensive logging, error handling
- **Scalable**: FAISS vector search for fast similarity operations on large catalogs

## Architecture

```
ai_service/
├── embeddings/           # CLIP embedder for images and text
│   └── clip_embedder.py
├── vector_db/            # FAISS index storage and search
│   └── product_index.py
├── indexing/             # Catalog indexing pipeline
│   └── catalog_indexer.py
├── recommendation/       # Recommendation engine with fashion rules
│   └── recommender.py
├── api/                  # FastAPI routes
│   └── routes.py
├── utils/                # Image loading and color analysis
│   ├── image_loader.py
│   └── color_utils.py
└── main.py              # FastAPI application
```

## Installation

### Requirements
- Python 3.9+
- CUDA 11.8+ (for GPU acceleration, optional)
- 8GB+ RAM (16GB+ recommended for full catalog)

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# For GPU support (CUDA 11.8)
pip install faiss-gpu

# Create .env file
cp .env.example .env
```

### Environment Variables

```env
# Model configuration
CLIP_MODEL_NAME=openai/clip-vit-base-patch32
EMBEDDING_DIM=512

# Service configuration
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
NUM_WORKERS=4
RELOAD=false
LOG_LEVEL=info

# Index paths
INDEX_PATH=/data/recommendation_index/faiss.index
METADATA_PATH=/data/recommendation_index/metadata.json

# Recommendation parameters
COLOR_WEIGHT=0.2
SIMILARITY_THRESHOLD=0.3

# CORS
CORS_ORIGINS=*
```

## API Endpoints

### 1. Index Catalog
**POST** `/api/v1/index-catalog`

Index Shopify products into the recommendation engine.

```bash
curl -X POST http://localhost:8000/api/v1/index-catalog \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {
        "id": 1,
        "title": "Classic White T-Shirt",
        "description": "Premium cotton t-shirt",
        "image_url": "https://example.com/tshirt.jpg",
        "category": "shirts",
        "tags": ["casual", "basic"]
      }
    ],
    "batch_size": 32
  }'
```

**Response:**
```json
{
  "total": 1,
  "successful": 1,
  "failed": 0,
  "index_size": 1,
  "failed_products": null
}
```

### 2. Visual Similarity
**GET** `/api/v1/recommend/similar`

Find visually similar products.

```bash
curl http://localhost:8000/api/v1/recommend/similar?product_id=1&top_k=10
```

**Response:**
```json
{
  "query_product_id": 1,
  "recommendations": [
    {
      "product_id": 5,
      "title": "Similar White Shirt",
      "category": "shirts",
      "similarity": 0.92
    }
  ],
  "total_count": 1
}
```

### 3. Style Matching
**GET** `/api/v1/recommend/style`

Find style-compatible items in different categories.

```bash
curl http://localhost:8000/api/v1/recommend/style?product_id=1&top_k=5
```

**Response:**
```json
{
  "query_product_id": 1,
  "recommendations": [
    {
      "product_id": 8,
      "title": "Navy Jeans",
      "category": "pants",
      "compatibility_score": 0.85
    }
  ],
  "total_count": 1
}
```

### 4. Complete the Look
**GET** `/api/v1/recommend/outfit`

Generate a complete coordinated outfit.

```bash
curl http://localhost:8000/api/v1/recommend/outfit?product_id=1&max_items=4
```

**Response:**
```json
{
  "base_product_id": 1,
  "base_category": "shirts",
  "total_items": 4,
  "outfit_score": 0.82,
  "outfit_items": [
    {
      "product_id": 1,
      "title": "Classic White T-Shirt",
      "category": "shirts",
      "role": "tops"
    },
    {
      "product_id": 8,
      "title": "Navy Jeans",
      "category": "pants",
      "role": "bottoms"
    }
  ]
}
```

### 5. Health Check
**GET** `/api/v1/health`

Check service health and index status.

```bash
curl http://localhost:8000/api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "indexed_products": 1000,
  "model": "openai/clip-vit-base-patch32",
  "device": "cuda:0"
}
```

## Running the Service

### Development

```bash
python main.py
```

Server will start at `http://localhost:8000`

API documentation available at `http://localhost:8000/docs`

### Production with Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 300 ai_service.main:app
```

### Docker

```bash
# Build image
docker build -t shopify-recommendation-engine .

# Run container
docker run -p 8000:8000 \
  -e CLIP_MODEL_NAME=openai/clip-vit-base-patch32 \
  -v /data:/data \
  shopify-recommendation-engine
```

## Usage Example

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Index products
products = [
    {
        "id": 1,
        "title": "White T-Shirt",
        "description": "Premium cotton tee",
        "image_url": "https://example.com/product1.jpg",
        "category": "shirts",
        "tags": ["casual", "basic"]
    },
    {
        "id": 2,
        "title": "Blue Jeans",
        "description": "Classic denim",
        "image_url": "https://example.com/product2.jpg",
        "category": "pants",
        "tags": ["casual", "denim"]
    }
]

response = requests.post(
    f"{BASE_URL}/index-catalog",
    json={
        "products": products,
        "batch_size": 32
    }
)
print("Index response:", response.json())

# Get similar products
similar = requests.get(
    f"{BASE_URL}/recommend/similar?product_id=1&top_k=5"
)
print("Similar products:", similar.json())

# Get style matches
style = requests.get(
    f"{BASE_URL}/recommend/style?product_id=1&top_k=5"
)
print("Style matches:", style.json())

# Get complete outfit
outfit = requests.get(
    f"{BASE_URL}/recommend/outfit?product_id=1&max_items=4"
)
print("Complete outfit:", outfit.json())
```

## Performance Optimization

### Vector Indexing
- **float32 vectors**: Uses 4 bytes per dimension for CPU/GPU efficiency
- **Normalized embeddings**: Enables cosine similarity via L2 distance
- **Batch processing**: Index products in batches of 32-256

### Model Loading
- **Single load**: CLIP model loaded once at startup
- **GPU acceleration**: Automatic CUDA detection and usage
- **Memory efficient**: Selective batch processing

### Recommendation Speed
- **O(log N) search**: FAISS IndexFlatL2 for exact nearest neighbors
- **Caching**: Embeddings cached in memory index
- **Batch queries**: Support for simultaneous requests

## Fashion Compatibility Rules

The system uses curated compatibility rules for outfit generation:

```
shirt → pants, jacket, shoes, belt, watch
pants → shirt, jacket, shoes, belt, watch
dress → heels, flats, shoes, bag, jacket
jacket → shirt, pants, dress, shoes, watch
shoes → shirt, pants, dress, jacket, socks
heels → dress, pants, skirt, bag
flats → dress, pants, skirt, shirt
bag → dress, shoes, accessories
skirt → shirt, heels, flats, shoes
sweater → pants, skirt, shoes, jacket
t-shirt → pants, jacket, shorts, shoes
shorts → t-shirt, shirt, shoes, jacket
belt → pants, shorts, dress
accessories → any
watch → any
socks → shoes, pants
```

## Embedding Strategy

### Multimodal Embedding (Default)
- **60% Image embedding**: Visual attributes
- **40% Text embedding**: Semantic meaning
- Normalized and combined for final vector

### Text-Only Fallback
- Used when image unavailable or fails
- Concatenates title + description
- Maximum token length: 77 (CLIP limit)

### Color Analysis
- Extracts 5 dominant colors from images
- Used for color compatibility scoring
- HSV color space for perceptual similarity

## Monitoring & Logging

- **Structured logging**: JSON format for log aggregation
- **Error tracking**: Comprehensive exception handling
- **Performance metrics**: Embedding generation times, search latency
- **Index statistics**: Product count, index size, search hit rates

## Production Checklist

- [x] Async FastAPI with concurrent request handling
- [x] Comprehensive error handling and validation
- [x] GPU support detection and configuration
- [x] Index persistence (save/load)
- [x] Background task support for large catalog indexing
- [x] Type hints on all public methods
- [x] Structured logging and monitoring
- [x] CORS configuration
- [x] Health check endpoint
- [x] Environment-based configuration
- [x] Docker containerization

## Troubleshooting

### Out of Memory
- Reduce batch size in indexing: `batch_size=16`
- Use CPU-only FAISS: `pip install faiss-cpu`
- Limit concurrent workers

### Slow Indexing
- Enable GPU FAISS if available
- Increase batch size for better throughput
- Verify network connection for image downloads

### Poor Recommendations
- Ensure products have descriptive titles/descriptions
- Use high-quality product images (min 200x200px)
- Verify category metadata is accurate
- Check color compatibility rules

## License

Part of the Shopify Fashion AI system. See LICENSE file.

## Support

For issues and questions, refer to:
- API Documentation: `/docs`
- Health check: `GET /api/v1/health`
- Logs: See service output
