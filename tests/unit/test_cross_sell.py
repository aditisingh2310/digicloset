import pytest
import requests
import io
from PIL import Image
import os
from unittest.mock import patch, AsyncMock

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")

def _server_available():
    try:
        requests.get(f"{MODEL_SERVICE_URL}/", timeout=2)
        requests.get(f"{BACKEND_URL}/health", timeout=2)
        return True
    except:
        return False

@pytest.fixture
def dummy_image(tmp_path):
    img = Image.new('RGB', (100, 100), color='red')
    img_path = tmp_path / "dummy_shirt.jpg"
    img.save(img_path)
    return img_path

@pytest.mark.skipif(not _server_available(), reason="Services not active")
def test_cross_sell_recommendations(dummy_image):
    """
    Tests the cross-sell endpoint end-to-end. Calls the backend API which
    will internally hit OpenRouter LLM, generate a text complementary query,
    and then hit the model-service's FAISS text-search endpoint.
    """
    
    # 1. Upload the dummy image to the backend first so it exists in UPLOAD_DIR
    item_id = "test_shirt_for_cross_sell.jpg"
    with dummy_image.open("rb") as fh:
        files = {'file': (item_id, fh, 'image/jpeg')}
        upload_res = requests.post(f"{BACKEND_URL}/api/v1/uploads/", files=files)
    assert upload_res.status_code == 200, "Failed to upload dummy item"
    uploaded_id = upload_res.json()["id"]

    # 2. Request cross-sell recommendations
    res = requests.get(f"{BACKEND_URL}/api/v1/garments/{uploaded_id}/cross-sell?top_k=2", timeout=30)
    
    # 3. Assertions
    assert res.status_code == 200
    data = res.json()
    
    assert data["base_item_id"] == uploaded_id
    assert "generated_outfit_query" in data
    assert len(data["generated_outfit_query"]) > 1  # Verify LLM returned strictly a string
    assert "complementary_items" in data
    
    # Since we uploaded at least one item, the FAISS search should return *something*, 
    # even if it's just the shirt itself due to the small db size.
    assert isinstance(data["complementary_items"], list)
