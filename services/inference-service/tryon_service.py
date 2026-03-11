"""
Virtual Try-On Service

High-level service for coordinating try-on generation.
Handles image fetching, API calls, and result storage.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import httpx

from .replicate_client import get_replicate_client, ReplicateError

logger = logging.getLogger(__name__)


@dataclass
class TryOnResult:
    """Result from try-on generation."""
    image_url: str
    processing_time: float
    prediction_id: str
    status: str = "success"
    error: Optional[str] = None


class TryOnService:
    """Service for virtual try-on generation."""

    def __init__(self, max_image_size: int = 10 * 1024 * 1024):
        """
        Initialize Try-On Service.

        Args:
            max_image_size: Maximum image size in bytes (default 10MB)
        """
        self.replicate_client = get_replicate_client()
        self.max_image_size = max_image_size
        self.image_download_timeout = 30  # seconds

    async def generate_tryon(
        self,
        user_image_url: str,
        garment_image_url: str,
        category: str = "upper_body",
        **kwargs,
    ) -> TryOnResult:
        """
        Generate virtual try-on image.

        Args:
            user_image_url: URL to user/person image
            garment_image_url: URL to garment/clothing image
            category: Garment category (upper_body, lower_body, dress)
            **kwargs: Additional parameters

        Returns:
            TryOnResult with generated image

        Raises:
            ValueError: Invalid inputs
            ReplicateError: API errors
        """
        try:
            # Validate inputs
            self._validate_urls(user_image_url, garment_image_url)

            # Download and validate images
            await self._validate_images(user_image_url, garment_image_url)

            logger.info(
                f"Starting try-on generation: user={user_image_url[:50]}..., "
                f"garment={garment_image_url[:50]}..."
            )

            # Call Replicate API
            result = await self.replicate_client.generate_tryon_image(
                user_image_url=user_image_url,
                garment_image_url=garment_image_url,
                category=category,
                **kwargs,
            )

            logger.info(
                f"Try-on generated successfully in {result['processing_time']:.2f}s"
            )

            return TryOnResult(
                image_url=result["image_url"],
                processing_time=result["processing_time"],
                prediction_id=result["prediction_id"],
                status="success",
            )

        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return TryOnResult(
                image_url="",
                processing_time=0,
                prediction_id="",
                status="error",
                error=str(e),
            )
        except ReplicateError as e:
            logger.error(f"Replicate API error: {str(e)}")
            return TryOnResult(
                image_url="",
                processing_time=0,
                prediction_id="",
                status="error",
                error=f"Generation failed: {str(e)}",
            )
        except Exception as e:
            logger.exception(f"Unexpected error in try-on generation: {str(e)}")
            return TryOnResult(
                image_url="",
                processing_time=0,
                prediction_id="",
                status="error",
                error="Internal server error",
            )

    @staticmethod
    def _validate_urls(user_image_url: str, garment_image_url: str) -> None:
        """Validate image URLs."""
        if not user_image_url or not isinstance(user_image_url, str):
            raise ValueError("user_image_url must be a non-empty string")

        if not garment_image_url or not isinstance(garment_image_url, str):
            raise ValueError("garment_image_url must be a non-empty string")

        if not user_image_url.startswith(("http://", "https://", "s3://")):
            raise ValueError("user_image_url must be a valid HTTP(S) or S3 URL")

        if not garment_image_url.startswith(("http://", "https://", "s3://")):
            raise ValueError("garment_image_url must be a valid HTTP(S) or S3 URL")

    async def _validate_images(
        self,
        user_image_url: str,
        garment_image_url: str,
    ) -> None:
        """
        Validate images are accessible and proper size.

        Args:
            user_image_url: User image URL
            garment_image_url: Garment image URL

        Raises:
            ValueError: Image validation failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.image_download_timeout) as client:
                # Check user image
                user_response = await client.head(user_image_url, follow_redirects=True)
                if user_response.status_code >= 400:
                    raise ValueError(f"Cannot access user image: {user_response.status_code}")

                size = int(user_response.headers.get("content-length", 0))
                if size > self.max_image_size:
                    raise ValueError(
                        f"User image too large: {size / 1024 / 1024:.1f}MB "
                        f"(max {self.max_image_size / 1024 / 1024:.1f}MB)"
                    )

                # Check garment image
                garment_response = await client.head(garment_image_url, follow_redirects=True)
                if garment_response.status_code >= 400:
                    raise ValueError(f"Cannot access garment image: {garment_response.status_code}")

                size = int(garment_response.headers.get("content-length", 0))
                if size > self.max_image_size:
                    raise ValueError(
                        f"Garment image too large: {size / 1024 / 1024:.1f}MB "
                        f"(max {self.max_image_size / 1024 / 1024:.1f}MB)"
                    )

        except httpx.RequestError as e:
            raise ValueError(f"Cannot download images: {str(e)}")


def get_tryon_service() -> TryOnService:
    """Get Try-On Service instance."""
    return TryOnService()
