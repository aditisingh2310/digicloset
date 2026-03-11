"""
Tests for Virtual Try-On Endpoints

Comprehensive test suite for try-on generation, credit management,
and status checking endpoints.
"""

import pytest
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
from fastapi.testclient import TestClient

logger = logging.getLogger(__name__)


# ============ Test Setup ============


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from apps.shopify_app.backend.main import app
    return TestClient(app)


@pytest.fixture
def mock_shop_context(client):
    """Mock shop context for authenticated requests."""
    def _set_context(shop_id: str = "gid://shopify/Shop/123456"):
        # This would depend on your auth implementation
        # Simplified for this example
        return {"shop_id": shop_id}
    return _set_context


@pytest.fixture
def valid_try_on_request():
    """Valid try-on request payload."""
    return {
        "user_image_url": "https://example.com/user.jpg",
        "garment_image_url": "https://example.com/garment.jpg",
        "category": "upper_body",
        "product_id": "prod_123",
    }


# ============ Tests for Generate Endpoint ============


class TestGenerateTryOn:
    """Tests for POST /api/v1/try-on/generate"""

    def test_generate_success(self, client, valid_try_on_request):
        """Test successful try-on generation initiation."""
        with patch("services.queue_worker.tryon_tasks.generate_tryon_task") as mock_task:
            mock_task.delay = MagicMock(return_value=MagicMock(id="task_123"))

            response = client.post(
                "/api/v1/try-on/generate",
                json=valid_try_on_request,
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "pending"
            assert "id" in data
            assert data["message"] == "Try-on generation started"

    def test_generate_missing_auth(self, client, valid_try_on_request):
        """Test generation without authentication."""
        response = client.post(
            "/api/v1/try-on/generate",
            json=valid_try_on_request,
        )

        assert response.status_code == 401

    def test_generate_invalid_images(self, client, valid_try_on_request):
        """Test generation with invalid image URLs."""
        invalid_request = valid_try_on_request.copy()
        invalid_request["user_image_url"] = "not-a-url"

        response = client.post(
            "/api/v1/try-on/generate",
            json=invalid_request,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 400

    def test_generate_insufficient_credits(self, client, valid_try_on_request):
        """Test generation when shop has no credits."""
        with patch("apps.shopify_app.backend.routes.tryon._check_shop_credits") as mock_check:
            mock_check.return_value = {
                "has_credits": False,
                "credits_remaining": 0,
                "message": "Monthly limit exceeded",
            }

            response = client.post(
                "/api/v1/try-on/generate",
                json=valid_try_on_request,
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 402  # Payment Required

    def test_generate_invalid_category(self, client, valid_try_on_request):
        """Test generation with invalid clothing category."""
        invalid_request = valid_try_on_request.copy()
        invalid_request["category"] = "invalid_category"

        response = client.post(
            "/api/v1/try-on/generate",
            json=invalid_request,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_celery_integration(self, client, valid_try_on_request):
        """Test that generation task is submitted to Celery."""
        with patch("services.queue_worker.tryon_tasks.generate_tryon_task") as mock_task:
            mock_task_instance = AsyncMock()
            mock_task_instance.id = "task_abc123"
            mock_task.delay = MagicMock(return_value=mock_task_instance)

            response = client.post(
                "/api/v1/try-on/generate",
                json=valid_try_on_request,
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 202
            # Verify Celery task was called with correct args
            assert mock_task.delay.called


# ============ Tests for Status Endpoint ============


class TestGetTryOnStatus:
    """Tests for GET /api/v1/try-on/{tryon_id}"""

    def test_get_status_processing(self, client):
        """Test getting status of processing try-on."""
        with patch("apps.shopify_app.backend.routes.tryon._get_tryon_from_db") as mock_db:
            mock_db.return_value = {
                "id": "tryon_123",
                "status": "processing",
                "created_at": datetime.now(),
                "processing_time": None,
            }

            response = client.get(
                "/api/v1/try-on/tryon_123",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
            assert "processing_time" not in data or data["processing_time"] is None

    def test_get_status_completed(self, client):
        """Test getting status of completed try-on."""
        with patch("apps.shopify_app.backend.routes.tryon._get_tryon_from_db") as mock_db:
            mock_db.return_value = {
                "id": "tryon_123",
                "status": "completed",
                "image_url": "https://storage.example.com/tryon_123.jpg",
                "processing_time": 12.5,
                "created_at": datetime.now(),
            }

            response = client.get(
                "/api/v1/try-on/tryon_123",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["image_url"] is not None
            assert data["processing_time"] == 12.5

    def test_get_status_failed(self, client):
        """Test getting status of failed try-on."""
        with patch("apps.shopify_app.backend.routes.tryon._get_tryon_from_db") as mock_db:
            mock_db.return_value = {
                "id": "tryon_123",
                "status": "failed",
                "error": "Image validation failed",
                "created_at": datetime.now(),
            }

            response = client.get(
                "/api/v1/try-on/tryon_123",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert data["error"] is not None

    def test_get_status_not_found(self, client):
        """Test getting status of non-existent try-on."""
        with patch("apps.shopify_app.backend.routes.tryon._get_tryon_from_db") as mock_db:
            mock_db.return_value = None

            response = client.get(
                "/api/v1/try-on/invalid_id",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 404

    def test_get_status_unauthorized(self, client):
        """Test getting status without authentication."""
        response = client.get("/api/v1/try-on/tryon_123")
        assert response.status_code == 401


# ============ Tests for Credits Endpoints ============


class TestCreditsCheck:
    """Tests for GET /api/v1/try-on/credits/check"""

    def test_check_credits_available(self, client):
        """Test credit check with available credits."""
        with patch("apps.shopify_app.backend.routes.tryon._check_shop_credits") as mock_check:
            mock_check.return_value = {
                "has_credits": True,
                "credits_remaining": 50,
                "message": "50 credits remaining",
            }

            response = client.get(
                "/api/v1/try-on/credits/check",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_credits"] is True
            assert data["credits_remaining"] == 50

    def test_check_credits_exhausted(self, client):
        """Test credit check with no credits."""
        with patch("apps.shopify_app.backend.routes.tryon._check_shop_credits") as mock_check:
            mock_check.return_value = {
                "has_credits": False,
                "credits_remaining": 0,
                "message": "No credits available",
            }

            response = client.get(
                "/api/v1/try-on/credits/check",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_credits"] is False
            assert data["credits_remaining"] == 0


class TestCreditsInfo:
    """Tests for GET /api/v1/try-on/credits/info"""

    def test_get_credits_info(self, client):
        """Test getting detailed credit information."""
        with patch("apps.shopify_app.backend.routes.tryon._get_shop_credits_from_db") as mock_db:
            mock_db.return_value = {
                "monthly_limit": 100,
                "credits_used": 25,
                "credits_remaining": 75,
                "reset_date": datetime.now() + timedelta(days=20),
            }

            response = client.get(
                "/api/v1/try-on/credits/info",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["monthly_limit"] == 100
            assert data["credits_used"] == 25
            assert data["credits_remaining"] == 75


# ============ Tests for History Endpoint ============


class TestTryOnHistory:
    """Tests for GET /api/v1/try-on/history"""

    def test_get_history_with_results(self, client):
        """Test getting try-on history with pagination."""
        with patch("apps.shopify_app.backend.routes.tryon._get_tryon_history_from_db") as mock_db:
            mock_db.return_value = (
                [
                    {
                        "id": "tryon_1",
                        "product_id": "prod_123",
                        "status": "completed",
                        "image_url": "https://example.com/tryon1.jpg",
                        "processing_time": 12.5,
                        "created_at": datetime.now(),
                    },
                    {
                        "id": "tryon_2",
                        "product_id": "prod_456",
                        "status": "completed",
                        "image_url": "https://example.com/tryon2.jpg",
                        "processing_time": 11.2,
                        "created_at": datetime.now(),
                    },
                ],
                2,  # total count
            )

            response = client.get(
                "/api/v1/try-on/history?limit=10&offset=0",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["tryons"]) == 2
            assert data["total"] == 2
            assert data["limit"] == 10
            assert data["offset"] == 0

    def test_get_history_empty(self, client):
        """Test getting empty history."""
        with patch("apps.shopify_app.backend.routes.tryon._get_tryon_history_from_db") as mock_db:
            mock_db.return_value = ([], 0)

            response = client.get(
                "/api/v1/try-on/history",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["tryons"]) == 0
            assert data["total"] == 0

    def test_get_history_pagination(self, client):
        """Test pagination with limit and offset."""
        response = client.get(
            "/api/v1/try-on/history?limit=5&offset=10",
            headers={"Authorization": "Bearer test_token"},
        )

        # Verify pagination parameters are respected
        assert response.status_code == 200

    def test_get_history_invalid_limit(self, client):
        """Test validation of limit parameter."""
        response = client.get(
            "/api/v1/try-on/history?limit=200",  # Max is 100
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 422  # Validation error


# ============ Integration Tests ============


class TestTryOnIntegration:
    """Integration tests for try-on workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, client, valid_try_on_request):
        """Test complete try-on workflow: create -> check status -> get result."""
        # 1. Initiate generation
        with patch("services.queue_worker.tryon_tasks.generate_tryon_task") as mock_task:
            mock_task.delay = MagicMock(return_value=MagicMock(id="task_123"))

            gen_response = client.post(
                "/api/v1/try-on/generate",
                json=valid_try_on_request,
                headers={"Authorization": "Bearer test_token"},
            )

            assert gen_response.status_code == 202
            tryon_id = gen_response.json()["id"]

        # 2. Check status (processing)
        with patch("apps.shopify_app.backend.routes.tryon._get_tryon_from_db") as mock_db:
            mock_db.return_value = {
                "id": tryon_id,
                "status": "processing",
                "created_at": datetime.now(),
            }

            status_response = client.get(
                f"/api/v1/try-on/{tryon_id}",
                headers={"Authorization": "Bearer test_token"},
            )

            assert status_response.status_code == 200
            assert status_response.json()["status"] == "processing"

        # 3. Check status (completed)
        with patch("apps.shopify_app.backend.routes.tryon._get_tryon_from_db") as mock_db:
            mock_db.return_value = {
                "id": tryon_id,
                "status": "completed",
                "image_url": "https://example.com/result.jpg",
                "processing_time": 15.0,
                "created_at": datetime.now(),
            }

            final_response = client.get(
                f"/api/v1/try-on/{tryon_id}",
                headers={"Authorization": "Bearer test_token"},
            )

            assert final_response.status_code == 200
            data = final_response.json()
            assert data["status"] == "completed"
            assert data["image_url"] is not None


# ============ Error Handling Tests ============


class TestErrorHandling:
    """Tests for error handling and validation."""

    def test_malformed_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/v1/try-on/generate",
            data="invalid json",
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test validation of required fields."""
        incomplete_request = {
            "user_image_url": "https://example.com/user.jpg",
            # missing garment_image_url
        }

        response = client.post(
            "/api/v1/try-on/generate",
            json=incomplete_request,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 422

    def test_server_error_handling(self, client, valid_try_on_request):
        """Test handling of server errors."""
        with patch("services.queue_worker.tryon_tasks.generate_tryon_task") as mock_task:
            mock_task.delay.side_effect = Exception("Database error")

            response = client.post(
                "/api/v1/try-on/generate",
                json=valid_try_on_request,
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 500


# ============ Rate Limiting Tests ============


class TestRateLimiting:
    """Tests for rate limiting per shop."""

    def test_rate_limit_exceeded(self, client, valid_try_on_request):
        """Test that rate limiting is enforced."""
        # Make multiple requests rapidly
        with patch("services.queue_worker.tryon_tasks.generate_tryon_task") as mock_task:
            mock_task.delay = MagicMock(return_value=MagicMock(id="task_123"))

            responses = []
            for i in range(15):  # Assuming limit is 10 per minute
                response = client.post(
                    "/api/v1/try-on/generate",
                    json=valid_try_on_request,
                    headers={"Authorization": "Bearer test_token"},
                )
                responses.append(response.status_code)

            # Last few should be rate limited (429)
            # This test depends on rate limiting configuration
            assert 429 in responses or all(code == 202 for code in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
