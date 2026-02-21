import pytest
import requests
import os
import base64

# Use the Docker network name for model-service
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")

def _server_available():
    import time
    for _ in range(150):
        try:
            r = requests.get(f"{MODEL_SERVICE_URL}/", timeout=5)
            if r.status_code == 200 and r.json().get("embeddings_active"):
                return True
        except Exception:
            pass
        time.sleep(2)
    return False

@pytest.fixture
def dummy_image(tmp_path):
    from PIL import Image
    img_path = tmp_path / "dummy.jpg"
    # Create a perfectly valid red square image to avoid 'truncated image' errors
    img = Image.new('RGB', (224, 224), color='red')
    img.save(img_path, format='JPEG')
    return img_path

@pytest.mark.skipif(not _server_available(), reason="Model service embedding API not active")
def test_embedding_generation(dummy_image):
    with dummy_image.open("rb") as fh:
        files = {'image': ('dummy.jpg', fh, 'image/jpeg')}
        r = requests.post(f"{MODEL_SERVICE_URL}/embeddings/generate", files=files, timeout=30)
    
    assert r.status_code == 200
    data = r.json()
    assert "embedding" in data
    assert isinstance(data["embedding"], list)
    assert len(data["embedding"]) == 512

@pytest.mark.skipif(not _server_available(), reason="Model service embedding API not active")
def test_embedding_add_and_search(dummy_image):
    # 1. Add item to FAISS
    item_id = "test_garment_001"
    with dummy_image.open("rb") as fh:
        files = {'image': ('dummy.jpg', fh, 'image/jpeg')}
        r_add = requests.post(f"{MODEL_SERVICE_URL}/embeddings/add?item_id={item_id}", files=files, timeout=30)
    
    assert r_add.status_code == 200
    assert r_add.json().get("item_id") == item_id

    # 2. Search FAISS with the same image
    with dummy_image.open("rb") as fh:
        files = {'image': ('dummy.jpg', fh, 'image/jpeg')}
        r_search = requests.post(f"{MODEL_SERVICE_URL}/embeddings/search?top_k=3", files=files, timeout=30)

    assert r_search.status_code == 200
    results = r_search.json().get("results", [])
    assert len(results) > 0
    
    # Since we searched with the exact same image, the top result should be highly similar (i.e. score near 1.0)
    # and match our item_id
    top_match = results[0]
    assert top_match["id"] == item_id
    assert top_match["score"] > 0.90
