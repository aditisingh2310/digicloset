# ========================================
# Shopify Fashion Recommendation Engine
# Production-Grade Multi-Stage Dockerfile
# ========================================

# ========== BUILDER STAGE ==========
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create wheels from requirements
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ========== RUNTIME STAGE ==========
FROM python:3.11-slim

LABEL maintainer="Shopify AI Team"
LABEL description="Fashion Recommendation Engine for Shopify"
LABEL version="1.0.0"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .

# Install Python dependencies from wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links /wheels -r requirements.txt && \
    rm -rf /wheels

# Copy application code
COPY . .

# Create data directory for indices
RUN mkdir -p /data/recommendation_index

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    SERVICE_HOST=0.0.0.0 \
    SERVICE_PORT=8000 \
    INDEX_PATH=/data/recommendation_index/faiss.index \
    METADATA_PATH=/data/recommendation_index/metadata.json \
    NUM_WORKERS=4 \
    LOG_LEVEL=info

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /data

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "ai_service.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4"]
