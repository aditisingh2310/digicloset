"""
Virtual Try-On Data Models

Pydantic models for API requests and responses.
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TryOnStatus(str, Enum):
    """Try-on generation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TryOnRequest(BaseModel):
    """Request model for try-on generation."""
    user_image_url: HttpUrl = Field(..., description="URL to user/person photo")
    garment_image_url: HttpUrl = Field(..., description="URL to garment/clothing photo")
    product_id: str = Field(..., description="Shopify product ID")
    shop_id: Optional[str] = Field(None, description="Shop ID (auto-populated by auth)")
    category: str = Field(default="upper_body", description="Garment category")

    @validator("category")
    def validate_category(cls, v):
        valid_categories = ["upper_body", "lower_body", "dress", "full_body"]
        if v not in valid_categories:
            raise ValueError(f"category must be one of {valid_categories}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "user_image_url": "https://example.com/user.jpg",
                "garment_image_url": "https://example.com/garment.jpg",
                "product_id": "gid://shopify/Product/123",
                "category": "upper_body"
            }
        }


class TryOnResponse(BaseModel):
    """Response model for try-on generation."""
    id: str = Field(..., description="Try-on generation ID")
    generated_image_url: Optional[str] = Field(None, description="URL to generated image")
    status: TryOnStatus = Field(..., description="Generation status")
    processing_time: Optional[float] = Field(None, description="Time taken in seconds")
    credits_used: int = Field(..., description="Credits used for this generation")
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        schema_extra = {
            "example": {
                "id": "tryon_123abc456",
                "generated_image_url": "https://storage.example.com/try-on.jpg",
                "status": "completed",
                "processing_time": 12.5,
                "credits_used": 1,
                "created_at": "2026-03-11T10:30:00Z",
                "completed_at": "2026-03-11T10:30:12Z"
            }
        }


class TryOnAsyncResponse(BaseModel):
    """Response for async try-on request."""
    id: str = Field(..., description="Try-on generation ID")
    status: TryOnStatus = Field(default=TryOnStatus.PENDING)
    message: str = "Try-on generation started"
    created_at: datetime

    class Config:
        schema_extra = {
            "example": {
                "id": "tryon_123abc456",
                "status": "pending",
                "message": "Try-on generation started",
                "created_at": "2026-03-11T10:30:00Z"
            }
        }


class TryOnStatusResponse(BaseModel):
    """Response for checking try-on status."""
    id: str
    status: TryOnStatus
    generated_image_url: Optional[str] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ShopCreditsResponse(BaseModel):
    """Response with shop credits info."""
    monthly_limit: int = Field(..., description="Total credits per month")
    credits_used: int = Field(..., description="Credits used this month")
    credits_remaining: int = Field(..., description="Credits remaining")
    reset_date: datetime = Field(..., description="When credits reset")

    class Config:
        schema_extra = {
            "example": {
                "monthly_limit": 100,
                "credits_used": 25,
                "credits_remaining": 75,
                "reset_date": "2026-04-11T00:00:00Z"
            }
        }


class CreditCheckResponse(BaseModel):
    """Response for credit availability check."""
    has_credits: bool = Field(..., description="Whether shop has available credits")
    credits_remaining: int = Field(..., description="Number of credits remaining")
    message: str = Field(..., description="Status message")


class TryOnHistoryResponse(BaseModel):
    """Single try-on in history."""
    id: str
    product_id: str
    generated_image_url: Optional[str]
    status: TryOnStatus
    credits_used: int
    processing_time: Optional[float]
    created_at: datetime


class TryOnHistoryListResponse(BaseModel):
    """Response model for try-on history list."""
    tryons: List[TryOnHistoryResponse]
    total: int = Field(..., description="Total number of try-ons")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Pagination offset")

    class Config:
        schema_extra = {
            "example": {
                "tryons": [],
                "total": 0,
                "limit": 10,
                "offset": 0
            }
        }
