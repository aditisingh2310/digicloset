"""
Shared pytest fixtures for the DigiCloset test suite.
"""

import os
import io
import time
import pytest
import requests
from pathlib import Path
from PIL import Image

MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


def _wait_for_service(url: str, timeout: int = 30) -> bool:
    """Wait for a service to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            time.sleep(1)
    return False


@pytest.fixture(scope="session")
def model_service_ready():
    """Ensures model-service is healthy before tests run."""
    assert _wait_for_service(f"{MODEL_SERVICE_URL}/"), "Model service did not start"
    return MODEL_SERVICE_URL


@pytest.fixture(scope="session")
def backend_ready():
    """Ensures backend is healthy before tests run."""
    assert _wait_for_service(f"{BACKEND_URL}/"), "Backend did not start"
    return BACKEND_URL


@pytest.fixture
def dummy_image(tmp_path) -> Path:
    """Creates a minimal valid JPEG image for testing."""
    img = Image.new("RGB", (100, 100), color=(128, 64, 200))
    path = tmp_path / "test_image.jpg"
    img.save(str(path), format="JPEG")
    return path


@pytest.fixture
def dummy_image_bytes() -> bytes:
    """Returns a minimal valid JPEG as bytes."""
    img = Image.new("RGB", (100, 100), color=(128, 64, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def large_image_bytes() -> bytes:
    """Returns a JPEG image that exceeds the 10MB upload limit."""
    img = Image.new("RGB", (5000, 5000), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=100)
    # If still not large enough, pad it
    data = buf.getvalue()
    if len(data) < 11 * 1024 * 1024:
        data += b"\x00" * (11 * 1024 * 1024 - len(data))
    return data


@pytest.fixture
def non_image_bytes() -> bytes:
    """Returns bytes that are NOT a valid image (for MIME rejection tests)."""
    return b"MZ" + b"\x00" * 500  # EXE-like header
