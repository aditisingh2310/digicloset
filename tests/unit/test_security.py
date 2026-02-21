"""
Security validation tests for the DigiCloset backend.
Tests file upload restrictions, path traversal protection, and MIME validation.
"""

import os
import pytest
import requests
import io
from PIL import Image

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")


def _server_available():
    try:
        return requests.get(f"{BACKEND_URL}/", timeout=3).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _server_available(), reason="Services not active")
class TestFileUploadSecurity:
    """Tests for upload endpoint security hardening."""

    def test_reject_non_image_extension(self):
        """Reject files with non-image extensions."""
        files = {'file': ('malware.exe', b'\x00' * 100, 'application/octet-stream')}
        r = requests.post(f"{BACKEND_URL}/api/v1/uploads/", files=files)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_reject_invalid_magic_bytes(self):
        """Reject files with valid extension but invalid magic bytes."""
        # EXE header disguised as .jpg
        fake_jpg = b"MZ" + b"\x00" * 500
        files = {'file': ('fake.jpg', fake_jpg, 'image/jpeg')}
        r = requests.post(f"{BACKEND_URL}/api/v1/uploads/", files=files)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_accept_valid_jpeg(self):
        """Accept a valid JPEG upload."""
        img = Image.new("RGB", (50, 50), color=(100, 150, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        files = {'file': ('valid.jpg', buf, 'image/jpeg')}
        r = requests.post(f"{BACKEND_URL}/api/v1/uploads/", files=files)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_accept_valid_png(self):
        """Accept a valid PNG upload."""
        img = Image.new("RGB", (50, 50), color=(200, 100, 50))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        files = {'file': ('valid.png', buf, 'image/png')}
        r = requests.post(f"{BACKEND_URL}/api/v1/uploads/", files=files)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


@pytest.mark.skipif(not _server_available(), reason="Services not active")
class TestPathTraversal:
    """Tests for path traversal protection in garments router."""

    def test_reject_path_traversal_dots(self):
        """Reject item IDs containing '..'."""
        r = requests.get(f"{BACKEND_URL}/api/v1/garments/../../etc/passwd/similar")
        assert r.status_code in (400, 404), f"Expected 400/404, got {r.status_code}"

    def test_reject_path_traversal_slash(self):
        """Reject item IDs containing forward slashes."""
        r = requests.get(f"{BACKEND_URL}/api/v1/garments/foo%2Fbar/colors")
        assert r.status_code in (400, 404), f"Expected 400/404, got {r.status_code}"


@pytest.mark.skipif(not _server_available(), reason="Services not active")
class TestModelServiceSizeGuard:
    """Tests for the model-service upload size guard."""

    def test_reject_oversized_upload(self):
        """Reject images exceeding the 10MB limit at model-service level."""
        # Create an oversized payload (just over 10MB of JPEG data)
        oversized = b"\xff\xd8\xff" + b"\x00" * (11 * 1024 * 1024)
        files = {'image': ('huge.jpg', oversized, 'image/jpeg')}
        r = requests.post(f"{MODEL_SERVICE_URL}/embeddings/generate", files=files, timeout=30)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
