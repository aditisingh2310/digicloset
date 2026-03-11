"""
Centralized configuration management for all services.

Environment variables are read from .env files and environment.
All services should use this module for configuration.
"""

import os
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    """Supported environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Config:
    """Base configuration for all services."""

    # Environment
    ENV = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/digicloset")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))

    # Shopify
    SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "")
    SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")
    SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")
    SHOPIFY_SCOPES = os.getenv("SHOPIFY_SCOPES", "write_products,read_customers")

    # AI/ML
    CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
    AI_INFERENCE_TIMEOUT = float(os.getenv("AI_INFERENCE_TIMEOUT", "30"))
    AI_CB_FAILURE_THRESHOLD = int(os.getenv("AI_CB_FAILURE_THRESHOLD", "3"))
    AI_CB_RESET_TIMEOUT = float(os.getenv("AI_CB_RESET_TIMEOUT", "30"))

    # Storage
    STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")  # local or s3
    S3_BUCKET = os.getenv("S3_BUCKET", "")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
    LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/tmp/digicloset-storage")

    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_WORKERS = int(os.getenv("API_WORKERS", "4"))

    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

    # Billing
    BILLING_ENABLED = os.getenv("BILLING_ENABLED", "true").lower() == "true"
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM = "HS256"
    TOKEN_EXPIRATION_HOURS = int(os.getenv("TOKEN_EXPIRATION_HOURS", "24"))

    # External APIs
    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

    # Queue Worker
    CELERY_BROKER = os.getenv("CELERY_BROKER", "redis://localhost:6379/1")
    CELERY_BACKEND = os.getenv("CELERY_BACKEND", "redis://localhost:6379/2")
    RQ_QUEUES = os.getenv("RQ_QUEUES", "ai,default").split(",")

    @classmethod
    def validate(cls) -> None:
        """Validate critical configuration on startup."""
        if not cls.SHOPIFY_API_KEY or not cls.SHOPIFY_API_SECRET:
            if cls.ENV == "production":
                raise ValueError("SHOPIFY_API_KEY and SHOPIFY_API_SECRET must be set in production")
        if cls.DATABASE_URL == "postgresql://user:password@localhost:5432/digicloset":
            if cls.ENV == "production":
                raise ValueError("DATABASE_URL must be configured for production")


# Create singleton config instance
config = Config()
