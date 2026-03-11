"""
Replicate API client for virtual try-on image generation.

Integrates with Replicate to send images and receive generated try-on results.
Handles API authentication, polling, and error handling.
"""

import os
import logging
import asyncio
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# Replicate API endpoints
REPLICATE_API_BASE = "https://api.replicate.com/v1"
TRYON_MODEL = "viton-hd"  # Virtual try-on model


class ReplicateError(Exception):
    """Base Replicate API error."""
    pass


class ReplicateTimeoutError(ReplicateError):
    """Prediction timed out."""
    pass


class ReplicateRateLimitError(ReplicateError):
    """Rate limit exceeded."""
    pass


class ReplicateAPIClient:
    """Client for Replicate API interactions."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        model: str = TRYON_MODEL,
        timeout: int = 300,  # 5 minutes
        poll_interval: float = 1.0,
    ):
        """
        Initialize Replicate API client.

        Args:
            api_token: Replicate API token (from REPLICATE_API_TOKEN env var)
            model: Model identifier (default: viton-hd)
            timeout: Timeout in seconds for generation
            poll_interval: Polling interval in seconds
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError("REPLICATE_API_TOKEN environment variable not set")

        self.model = model
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.base_url = REPLICATE_API_BASE

    async def generate_tryon_image(
        self,
        user_image_url: str,
        garment_image_url: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate virtual try-on image using Replicate API.

        Args:
            user_image_url: URL to user/person image
            garment_image_url: URL to garment/clothing image
            **kwargs: Additional model parameters

        Returns:
            Dictionary with:
                - image_url: Generated image URL or base64
                - processing_time: Generation time in seconds
                - prediction_id: Replicate prediction ID
                - status: "success" or "error"

        Raises:
            ReplicateError: API errors
            ReplicateTimeoutError: Generation timeout
        """
        start_time = datetime.now()

        try:
            # Create prediction
            prediction_id = await self._create_prediction(
                user_image_url=user_image_url,
                garment_image_url=garment_image_url,
                **kwargs,
            )
            logger.info(f"Created prediction: {prediction_id}")

            # Poll for result
            result_url = await self._poll_prediction(prediction_id)

            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "image_url": result_url,
                "processing_time": processing_time,
                "prediction_id": prediction_id,
                "status": "success",
            }

        except ReplicateTimeoutError as e:
            logger.error(f"Prediction timed out: {str(e)}")
            raise
        except ReplicateError as e:
            logger.error(f"Replicate API error: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in try-on generation: {str(e)}")
            raise ReplicateError(f"Generation failed: {str(e)}")

    async def _create_prediction(
        self,
        user_image_url: str,
        garment_image_url: str,
        **kwargs,
    ) -> str:
        """
        Create a prediction on Replicate.

        Args:
            user_image_url: Person image URL
            garment_image_url: Garment image URL
            **kwargs: Additional parameters

        Returns:
            Prediction ID

        Raises:
            ReplicateError: API errors
        """
        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }

        # Build input for viton-hd model
        input_data = {
            "human_img": user_image_url,
            "cloth_img": garment_image_url,
            # Optional parameters
            "category": kwargs.get("category", "upper_body"),
            "seed": kwargs.get("seed", -1),
            **{k: v for k, v in kwargs.items() if k not in ["category", "seed"]},
        }

        # Use appropriate model version
        model_version = kwargs.get(
            "model_version",
            "f1b63e0b0fb5c3ee94346c1e2e1a5a4c5c3a5f8d9b",  # Example version
        )

        payload = {
            "version": model_version,
            "input": input_data,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/predictions",
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 429:
                    raise ReplicateRateLimitError("Rate limit exceeded")
                elif response.status_code >= 400:
                    error_data = response.json() if response.text else {}
                    raise ReplicateError(
                        f"Failed to create prediction: {response.status_code} - {error_data}"
                    )

                result = response.json()
                return result["id"]

        except httpx.TimeoutException as e:
            raise ReplicateError(f"Request timeout: {str(e)}")
        except httpx.HTTPError as e:
            raise ReplicateError(f"HTTP error: {str(e)}")

    async def _poll_prediction(
        self,
        prediction_id: str,
    ) -> str:
        """
        Poll Replicate API until prediction completes.

        Args:
            prediction_id: Prediction ID from create_prediction

        Returns:
            Generated image URL

        Raises:
            ReplicateTimeoutError: Prediction timeout
            ReplicateError: API errors or failed prediction
        """
        headers = {
            "Authorization": f"Token {self.api_token}",
        }

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=self.timeout)

        while datetime.now() < end_time:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(
                        f"{self.base_url}/predictions/{prediction_id}",
                        headers=headers,
                    )

                    if response.status_code >= 400:
                        raise ReplicateError(
                            f"Failed to get prediction: {response.status_code}"
                        )

                    data = response.json()
                    status = data.get("status")

                    if status == "succeeded":
                        output = data.get("output")
                        # Output can be a list or string URL
                        if isinstance(output, list) and output:
                            return output[0]
                        return output

                    elif status == "failed":
                        error_msg = data.get("error", "Unknown error")
                        raise ReplicateError(f"Prediction failed: {error_msg}")

                    elif status in ["processing", "starting"]:
                        logger.debug(f"Prediction {prediction_id} status: {status}")
                        await asyncio.sleep(self.poll_interval)
                        continue

                    else:
                        raise ReplicateError(f"Unknown status: {status}")

            except httpx.TimeoutException:
                logger.warning(f"Timeout polling prediction {prediction_id}")
                await asyncio.sleep(self.poll_interval)
                continue
            except httpx.HTTPError as e:
                logger.error(f"HTTP error polling: {str(e)}")
                await asyncio.sleep(self.poll_interval)
                continue

        raise ReplicateTimeoutError(
            f"Prediction {prediction_id} did not complete within {self.timeout}s"
        )

    async def cancel_prediction(self, prediction_id: str) -> bool:
        """
        Cancel an ongoing prediction.

        Args:
            prediction_id: Prediction ID

        Returns:
            True if cancelled, False otherwise
        """
        headers = {
            "Authorization": f"Token {self.api_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/predictions/{prediction_id}/cancel",
                    headers=headers,
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to cancel prediction: {str(e)}")
            return False

    async def get_prediction_status(self, prediction_id: str) -> Dict[str, Any]:
        """
        Get status of a prediction.

        Args:
            prediction_id: Prediction ID

        Returns:
            Prediction status object
        """
        headers = {
            "Authorization": f"Token {self.api_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/predictions/{prediction_id}",
                    headers=headers,
                )

                if response.status_code >= 400:
                    raise ReplicateError(
                        f"Failed to get status: {response.status_code}"
                    )

                return response.json()

        except Exception as e:
            logger.error(f"Failed to get prediction status: {str(e)}")
            raise


# Singleton instance for easy access
_client_instance: Optional[ReplicateAPIClient] = None


def get_replicate_client() -> ReplicateAPIClient:
    """Get or create Replicate API client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ReplicateAPIClient()
    return _client_instance
