"""
Performance validation tests for the DigiCloset model-service.
Tests image preprocessing, cache behavior, and latency thresholds.
"""

import os
import io
import time
import pytest
import requests
from PIL import Image

MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")


def _server_available():
    try:
        return requests.get(f"{MODEL_SERVICE_URL}/", timeout=3).status_code == 200
    except Exception:
        return False


def _create_test_image(width=800, height=800) -> bytes:
    """Creates a test image of given dimensions."""
    img = Image.new("RGB", (width, height), color=(64, 128, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.skipif(not _server_available(), reason="Model service not active")
class TestImagePreprocessing:
    """Tests that images are properly preprocessed (resized) before ML inference."""

    def test_large_image_embedding_succeeds(self):
        """A large image (1024x1024) should still produce a valid 512d embedding."""
        large_img = _create_test_image(1024, 1024)
        files = {'image': ('large.jpg', large_img, 'image/jpeg')}
        r = requests.post(f"{MODEL_SERVICE_URL}/embeddings/generate", files=files, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data["embedding"]) == 512


@pytest.mark.skipif(not _server_available(), reason="Model service not active")
class TestCacheBehavior:
    """Tests the LRU cache for embedding inference."""

    def test_cache_hit_on_duplicate_image(self):
        """Sending the same image twice should result in a cache hit on the second call."""
        img_bytes = _create_test_image(256, 256)
        files1 = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
        r1 = requests.post(f"{MODEL_SERVICE_URL}/embeddings/generate", files=files1, timeout=30)
        assert r1.status_code == 200

        files2 = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
        r2 = requests.post(f"{MODEL_SERVICE_URL}/embeddings/generate", files=files2, timeout=30)
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2.get("cache") == "hit", "Expected cache hit on duplicate image"

    def test_different_images_produce_different_embeddings(self):
        """Two different images should produce different embeddings."""
        img1 = _create_test_image(100, 100)
        img2 = Image.new("RGB", (100, 100), color=(255, 0, 0))
        buf2 = io.BytesIO()
        img2.save(buf2, format="JPEG")
        img2_bytes = buf2.getvalue()

        files1 = {'image': ('img1.jpg', img1, 'image/jpeg')}
        r1 = requests.post(f"{MODEL_SERVICE_URL}/embeddings/generate", files=files1, timeout=30)
        files2 = {'image': ('img2.jpg', img2_bytes, 'image/jpeg')}
        r2 = requests.post(f"{MODEL_SERVICE_URL}/embeddings/generate", files=files2, timeout=30)

        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["embedding"] != r2.json()["embedding"]


@pytest.mark.skipif(not _server_available(), reason="Model service not active")
class TestLatency:
    """Tests that AI endpoints respond within acceptable latency thresholds."""

    def test_embedding_latency_under_threshold(self):
        """Embedding generation should complete within 10 seconds."""
        img_bytes = _create_test_image(256, 256)
        files = {'image': ('perf.jpg', img_bytes, 'image/jpeg')}
        start = time.time()
        r = requests.post(f"{MODEL_SERVICE_URL}/embeddings/generate", files=files, timeout=15)
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 10.0, f"Embedding took {elapsed:.1f}s, expected <10s"

    def test_health_endpoint_fast(self):
        """Health endpoint should respond in under 500ms."""
        start = time.time()
        r = requests.get(f"{MODEL_SERVICE_URL}/health", timeout=5)
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 0.5, f"Health check took {elapsed:.1f}s, expected <0.5s"

    def test_metrics_endpoint_available(self):
        """Metrics endpoint should return valid JSON."""
        r = requests.get(f"{MODEL_SERVICE_URL}/metrics", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "requests_total" in data
        assert "latency" in data
