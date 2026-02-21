# DigiCloset Architecture (C4 Model)

## Context Diagram

```mermaid
graph LR
    Merchant["Shopify Merchant"] -->|Upload Products| Frontend["DigiCloset App"]
    Frontend -->|REST API| Backend["Backend Service"]
    Backend -->|ML Inference| ModelService["Model Service"]
    Backend -->|Vision LLM| OpenRouter["OpenRouter API"]
    ModelService -->|Vector Search| FAISS["FAISS Index"]
```

## Container Diagram

```mermaid
graph TB
    subgraph "DigiCloset Platform"
        subgraph "Backend Service :8000"
            Auth["Auth Router"]
            Uploads["Upload Router"]
            Garments["Garments Router"]
            Infer["Infer Router"]
            Security["Security Middleware"]
            RateLimiter["Rate Limiter (slowapi)"]
            StylistService["Stylist Service (OpenRouter)"]
        end
        
        subgraph "Model Service :8001"
            Embeddings["Embedding Service (OpenCLIP ViT-B-32)"]
            VectorStore["FAISS Vector Store"]
            ColorExtractor["Color Extractor (KMeans)"]
            RankingService["Ranking Service (EMA Personalization)"]
            BgRemoval["Background Removal (U-2-Net)"]
            Cache["LRU Cache Layer"]
            Metrics["Metrics Middleware"]
            Health["Health/Readiness Probes"]
            ImageUtils["Image Preprocessor (512px)"]
        end
    end

    Uploads --> Security
    Uploads --> Embeddings
    Garments --> StylistService
    StylistService --> Embeddings
    Embeddings --> Cache
    Embeddings --> VectorStore
```

## Component: ML Inference Pipeline

```mermaid
flowchart LR
    A["Upload Image"] --> B["Validate (MIME, Size, Extension)"]
    B --> C["Preprocess (Resize 512px, RGB)"]
    C --> D{"Cache Hit?"}
    D -->|Yes| E["Return Cached Embedding"]
    D -->|No| F["OpenCLIP ViT-B-32"]
    F --> G["512-dim Vector"]
    G --> H["Store in FAISS"]
    G --> I["Cache (SHA-256 key)"]
    H --> J["Similarity Search"]
```

## Data Flow: Cross-Sell Recommendation

```mermaid
sequenceDiagram
    participant Client
    participant Backend
    participant OpenRouter
    participant ModelService
    participant FAISS

    Client->>Backend: GET /garments/{id}/cross-sell
    Backend->>Backend: Load garment image
    Backend->>OpenRouter: Vision LLM (Llama 3.2 11B)
    OpenRouter-->>Backend: "dark wash denim jeans"
    Backend->>ModelService: GET /embeddings/search-text?query=...
    ModelService->>ModelService: OpenCLIP text encoder → 512d vector
    ModelService->>FAISS: Nearest neighbor search
    FAISS-->>ModelService: Top-K similar items
    ModelService-->>Backend: Results
    Backend-->>Client: Complementary items
```

## Failure Modes & Recovery

| Failure | Impact | Recovery |
|---------|--------|----------|
| Model-service down | Uploads succeed but embeddings fail silently | Backend logs warning, retries on next access |
| FAISS index empty | Similar/cross-sell return empty results | Graceful empty response, no crash |
| OpenRouter rate-limited | Cross-sell returns fallback query | `stylist_service.py` catches exception, returns "black outfit accessory" |
| Oversized upload | Rejected at both backend (MIME) and model-service (10MB guard) | HTTP 400 with descriptive error |
| Cache full | Oldest entries evicted via LRU | Transparent to caller, slight latency increase |

## Security Layers

| Layer | Implementation | Location |
|-------|---------------|----------|
| CORS | Configurable origin allowlist | `backend/main.py` |
| Rate Limiting | slowapi (30 req/min upload, 10/min cross-sell, 5/min bg-removal) | `backend/main.py`, `garments.py` |
| SSRF Protection | Domain allowlist + private IP blocking | `security.py` |
| MIME Validation | Magic byte verification | `security.py` → `uploads.py` |
| Path Traversal | Regex sanitization of item IDs | `security.py` → `garments.py` |
| Input Sanitization | XSS character stripping middleware | `security.py` |
| Size Limits | 10MB at backend + model-service | `uploads.py`, `serve.py` |
