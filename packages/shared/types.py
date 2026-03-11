"""
Shared type definitions and schemas used across the monorepo.
"""

from typing import Generic, TypeVar, List, Optional, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


T = TypeVar("T")


class Status(str, Enum):
    """Standard status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    PROCESSING = "processing"


class APIResponse(BaseModel, Generic[T]):
    """Standard API response format."""
    status: Status
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    status: str = "error"
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=100)


class AiResultSchema(BaseModel):
    """AI result from analysis."""
    id: str
    shop: str
    product_id: str
    request_id: Optional[str] = None
    category: str
    tags: Dict[str, Any]
    confidence: float
    created_at: str


class ShopSchema(BaseModel):
    """Shop/merchant information."""
    id: int
    shop_domain: str
    access_token: str
    scope: Optional[str] = None
    subscription_status: str = "inactive"
    installed_at: str


class RecommendationSchema(BaseModel):
    """Product recommendation."""
    product_id: str
    name: str
    image_url: Optional[str] = None
    price: float
    confidence_score: float
    reason: Optional[str] = None


class OutfitSchema(BaseModel):
    """Outfit bundle."""
    id: str
    shop_id: str
    name: str
    description: Optional[str] = None
    items: List[RecommendationSchema]
    created_at: str
    updated_at: str
