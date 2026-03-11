"""
Tests for Replicate API Client

Comprehensive test suite for Replicate API integration including
polling, error handling, and timeout scenarios.
"""

import pytest
import logging
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import httpx

from services.inference_service.replicate_client import (
    ReplicateAPIClient,
    ReplicateError,
    ReplicateTimeoutError,
    ReplicateRateLimitError,
    get_replicate_client,
)

logger = logging.getLogger(__name__)


# ============ Test Setup ============


@pytest.fixture
def mock_api_token(monkeypatch):
    """Set mock Replicate API token."""
    monkeypatch.setenv("REPLICATE_API_TOKEN", "test_token_123")
    return "test_token_123"


@pytest.fixture
def client(mock_api_token):
    """Create ReplicateAPIClient instance."""
    return ReplicateAPIClient(api_token=mock_api_token)


@pytest.fixture
def valid_prediction_response():
    """Valid Replicate API prediction response."""
    return {
        "id": "pred_abc123",
        "model": "api/try-on-model",
        "version": "v1.0.0",
        "input": {
            "user_image": "https://example.com/user.jpg",
            "garment_image": "https://example.com/garment.jpg",
        },
        "output": ["https://replicate.com/output/tryon.jpg"],
        "status": "succeeded",
        "created_at": datetime.now().isoformat(),
        "started_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
    }


@pytest.fixture
def processing_prediction_response():
    """Processing Replicate API prediction response."""
    return {
        "id": "pred_processing123",
        "model": "api/try-on-model",
        "version": "v1.0.0",
        "input": {
            "user_image": "https://example.com/user.jpg",
            "garment_image": "https://example.com/garment.jpg",
        },
        "output": None,
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "started_at": datetime.now().isoformat(),
    }


# ============ Tests for Create Prediction ============


class TestCreatePrediction:
    """Tests for create_prediction method."""

    @pytest.mark.asyncio
    async def test_create_prediction_success(self, client, valid_prediction_response):
        """Test successful prediction creation."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=valid_prediction_response)
            mock_response.status_code = 201
            mock_post.return_value = mock_response

            result = await client._create_prediction(
                user_image_url="https://example.com/user.jpg",
                garment_image_url="https://example.com/garment.jpg",
            )

            assert result["id"] == "pred_abc123"
            assert result["status"] == "succeeded"

    @pytest.mark.asyncio
    async def test_create_prediction_401_unauthorized(self, client):
        """Test prediction creation with invalid token."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.return_value = mock_response

            with pytest.raises(ReplicateError) as exc_info:
                await client._create_prediction(
                    user_image_url="https://example.com/user.jpg",
                    garment_image_url="https://example.com/garment.jpg",
                )

            assert "401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_prediction_429_rate_limit(self, client):
        """Test prediction creation with rate limiting."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_post.return_value = mock_response

            with pytest.raises(ReplicateRateLimitError):
                await client._create_prediction(
                    user_image_url="https://example.com/user.jpg",
                    garment_image_url="https://example.com/garment.jpg",
                )

    @pytest.mark.asyncio
    async def test_create_prediction_network_error(self, client):
        """Test prediction creation with network error."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Network error")

            with pytest.raises(ReplicateError):
                await client._create_prediction(
                    user_image_url="https://example.com/user.jpg",
                    garment_image_url="https://example.com/garment.jpg",
                )


# ============ Tests for Poll Prediction ============


class TestPollPrediction:
    """Tests for poll_prediction method (async polling)."""

    @pytest.mark.asyncio
    async def test_poll_prediction_immediate_success(
        self, client, valid_prediction_response
    ):
        """Test polling when prediction completes immediately."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=valid_prediction_response)
            mock_get.return_value = mock_response

            result = await client._poll_prediction(
                prediction_id="pred_abc123",
                timeout=30,
                interval=1,
            )

            assert result["status"] == "succeeded"
            assert result["output"] is not None

    @pytest.mark.asyncio
    async def test_poll_prediction_eventual_success(
        self, client, processing_prediction_response, valid_prediction_response
    ):
        """Test polling with multiple status checks before completion."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # First call returns processing, second returns completed
            processing_response = AsyncMock()
            processing_response.json = AsyncMock(
                return_value=processing_prediction_response
            )

            completed_response = AsyncMock()
            completed_response.json = AsyncMock(return_value=valid_prediction_response)

            mock_get.side_effect = [processing_response, completed_response]

            result = await client._poll_prediction(
                prediction_id="pred_processing123",
                timeout=30,
                interval=1,
            )

            assert result["status"] == "succeeded"
            # Verify polling happened multiple times
            assert mock_get.call_count >= 2

    @pytest.mark.asyncio
    async def test_poll_prediction_timeout(self, client, processing_prediction_response):
        """Test polling timeout after max wait time."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=processing_prediction_response)
            mock_get.return_value = mock_response

            with pytest.raises(ReplicateTimeoutError):
                await client._poll_prediction(
                    prediction_id="pred_processing123",
                    timeout=1,  # 1 second timeout
                    interval=0.5,  # Poll every 0.5 seconds
                )

    @pytest.mark.asyncio
    async def test_poll_prediction_failed_status(self, client):
        """Test polling when prediction fails."""
        failed_response = {
            "id": "pred_failed123",
            "status": "failed",
            "error": "Invalid input image",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=failed_response)
            mock_get.return_value = mock_response

            result = await client._poll_prediction(
                prediction_id="pred_failed123",
                timeout=30,
            )

            assert result["status"] == "failed"
            assert "error" in result


# ============ Tests for Generate Try-On ============


class TestGenerateTryOnImage:
    """Tests for generate_tryon_image main method."""

    @pytest.mark.asyncio
    async def test_generate_tryon_success(
        self, client, valid_prediction_response
    ):
        """Test successful try-on image generation."""
        # Mock both create and poll operations
        with patch.object(client, "_create_prediction") as mock_create:
            with patch.object(client, "_poll_prediction") as mock_poll:
                mock_create.return_value = {
                    "id": "pred_abc123",
                    "status": "processing",
                }
                mock_poll.return_value = valid_prediction_response

                result = await client.generate_tryon_image(
                    user_image_url="https://example.com/user.jpg",
                    garment_image_url="https://example.com/garment.jpg",
                )

                assert result.prediction_id == "pred_abc123"
                assert result.image_url == "https://replicate.com/output/tryon.jpg"
                assert result.status == "succeeded"
                mock_create.assert_called_once()
                mock_poll.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_tryon_with_timeout(self, client):
        """Test try-on generation with timeout."""
        with patch.object(client, "_create_prediction") as mock_create:
            with patch.object(client, "_poll_prediction") as mock_poll:
                mock_create.return_value = {
                    "id": "pred_timeout123",
                    "status": "processing",
                }
                mock_poll.side_effect = ReplicateTimeoutError(
                    "Prediction took too long"
                )

                with pytest.raises(ReplicateTimeoutError):
                    await client.generate_tryon_image(
                        user_image_url="https://example.com/user.jpg",
                        garment_image_url="https://example.com/garment.jpg",
                        timeout=10,
                    )

    @pytest.mark.asyncio
    async def test_generate_tryon_rate_limited(self, client):
        """Test try-on generation with rate limiting."""
        with patch.object(client, "_create_prediction") as mock_create:
            mock_create.side_effect = ReplicateRateLimitError(
                "Rate limit exceeded"
            )

            with pytest.raises(ReplicateRateLimitError):
                await client.generate_tryon_image(
                    user_image_url="https://example.com/user.jpg",
                    garment_image_url="https://example.com/garment.jpg",
                )


# ============ Tests for Cancel Prediction ============


class TestCancelPrediction:
    """Tests for cancel_prediction method."""

    @pytest.mark.asyncio
    async def test_cancel_prediction_success(self, client):
        """Test successful prediction cancellation."""
        cancel_response = {
            "id": "pred_cancel123",
            "status": "canceled",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=cancel_response)
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = await client.cancel_prediction("pred_cancel123")

            assert result["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_prediction_not_found(self, client):
        """Test canceling non-existent prediction."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.text = "Not found"
            mock_post.return_value = mock_response

            with pytest.raises(ReplicateError):
                await client.cancel_prediction("pred_notfound")


# ============ Tests for Get Prediction Status ============


class TestGetPredictionStatus:
    """Tests for get_prediction_status method."""

    @pytest.mark.asyncio
    async def test_get_status_success(self, client, valid_prediction_response):
        """Test successfully retrieving prediction status."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=valid_prediction_response)
            mock_get.return_value = mock_response

            result = await client.get_prediction_status("pred_abc123")

            assert result["id"] == "pred_abc123"
            assert result["status"] == "succeeded"

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client):
        """Test getting status of non-existent prediction."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.text = "Not found"
            mock_get.return_value = mock_response

            with pytest.raises(ReplicateError):
                await client.get_prediction_status("pred_notfound")


# ============ Tests for Singleton Pattern ============


class TestSingletonPattern:
    """Tests for ReplicateAPIClient singleton."""

    def test_get_replicate_client_singleton(self, mock_api_token):
        """Test that get_replicate_client returns singleton instance."""
        client1 = get_replicate_client()
        client2 = get_replicate_client()

        assert client1 is client2

    def test_singleton_uses_env_token(self, monkeypatch, mock_api_token):
        """Test singleton uses API token from environment."""
        # Reset singleton
        import services.inference_service.replicate_client as rc_module
        rc_module._replicate_client = None

        monkeypatch.setenv("REPLICATE_API_TOKEN", "env_token_123")

        client = get_replicate_client()
        assert client.api_token == "env_token_123"


# ============ Integration Tests ============


class TestReplicateIntegration:
    """Integration tests with Replicate-like API."""

    @pytest.mark.asyncio
    async def test_full_generation_workflow(self, client, valid_prediction_response):
        """Test complete workflow: create -> poll -> complete."""
        with patch("httpx.AsyncClient") as mock_async_client:
            # Create prediction
            create_response = AsyncMock()
            create_response.json = AsyncMock(return_value={
                "id": "pred_workflow123",
                "status": "processing",
            })
            create_response.status_code = 201

            # Poll prediction (returns processing then success)
            processing_response = AsyncMock()
            processing_response.json = AsyncMock(return_value={
                "id": "pred_workflow123",
                "status": "processing",
            })

            completed_response = AsyncMock()
            completed_response.json = AsyncMock(return_value=valid_prediction_response)

            mock_instance = AsyncMock()
            mock_instance.post.return_value = create_response
            mock_instance.get.side_effect = [processing_response, completed_response]

            with patch("httpx.AsyncClient") as mock_context:
                mock_context.return_value.__aenter__.return_value = mock_instance

                result = await client.generate_tryon_image(
                    user_image_url="https://example.com/user.jpg",
                    garment_image_url="https://example.com/garment.jpg",
                    timeout=30,
                )

                assert result.prediction_id == "pred_workflow123"


# ============ Error Type Tests ============


class TestErrorTypes:
    """Tests for custom error types."""

    def test_replicate_error_message(self):
        """Test ReplicateError has proper message."""
        error = ReplicateError("API error occurred")
        assert str(error) == "API error occurred"

    def test_timeout_error_inheritance(self):
        """Test ReplicateTimeoutError inherits from ReplicateError."""
        error = ReplicateTimeoutError("Timeout")
        assert isinstance(error, ReplicateError)

    def test_rate_limit_error_inheritance(self):
        """Test ReplicateRateLimitError inherits from ReplicateError."""
        error = ReplicateRateLimitError("Rate limited")
        assert isinstance(error, ReplicateError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
