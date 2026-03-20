"""Main FastAPI application for recommendation service."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import torch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
embedder = None
vector_index = None
recommender = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    
    Startup: Load models and initialize components
    Shutdown: Clean up resources
    """
    global embedder, vector_index, recommender
    
    # Startup
    logger.info("Starting recommendation service...")
    try:
        from ai_service.embeddings import CLIPEmbedder
        from ai_service.vector_db import ProductVectorIndex
        from ai_service.recommendation import Recommender
        
        # Initialize embedder
        model_name = os.getenv(
            "CLIP_MODEL_NAME",
            "openai/clip-vit-base-patch32"
        )
        logger.info(f"Loading CLIP model: {model_name}")
        embedder = CLIPEmbedder(model_name=model_name)
        
        # Initialize vector index
        embedding_dim = os.getenv("EMBEDDING_DIM", "512")
        vector_index = ProductVectorIndex(embedding_dim=int(embedding_dim))
        
        # Load existing index if available
        index_path = os.getenv(
            "INDEX_PATH",
            "/tmp/recommendation_index/faiss.index"
        )
        metadata_path = os.getenv(
            "METADATA_PATH",
            "/tmp/recommendation_index/metadata.json"
        )
        
        if os.path.exists(index_path):
            try:
                logger.info("Loading existing index from disk...")
                vector_index.load(index_path, metadata_path)
                logger.info(f"Loaded {vector_index.get_size()} products")
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}")
        
        # Initialize recommender
        recommender = Recommender(
            vector_index,
            color_weight=float(os.getenv("COLOR_WEIGHT", "0.2")),
            similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
        )
        
        logger.info("Service initialized successfully")
    
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    
    yield  # Application running
    
    # Shutdown
    logger.info("Shutting down recommendation service...")
    try:
        # Save index before shutdown
        if vector_index and vector_index.get_size() > 0:
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            vector_index.save(index_path, metadata_path)
            logger.info("Saved index to disk")
        
        # Clear GPU memory
        if embedder and torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("Cleared GPU memory")
    
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Shopify Fashion Recommendation Engine",
    description="Visual and multimodal recommendation system for fashion products",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Mount routes
@app.on_event("startup")
async def startup_routes():
    """Initialize and mount API routes."""
    if embedder and vector_index and recommender:
        from ai_service.api.routes import create_router
        
        router = create_router(embedder, vector_index, recommender)
        app.include_router(router)
        logger.info("API routes mounted")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Shopify Fashion Recommendation Engine",
        "version": "1.0.0",
        "status": "running",
        "indexed_products": vector_index.get_size() if vector_index else 0,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8000"))
    workers = int(os.getenv("NUM_WORKERS", "1"))
    
    logger.info(f"Starting service on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=workers,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
