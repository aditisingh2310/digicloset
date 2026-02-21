import pytest
import requests
import os
import time

MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")

def _server_available():
    for _ in range(150):
        try:
            r = requests.get(f"{MODEL_SERVICE_URL}/", timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False

@pytest.fixture
def dummy_image(tmp_path):
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='green')
    img_path = tmp_path / "dummy.jpg"
    img.save(img_path, format='JPEG')
    return img_path

@pytest.mark.skipif(not _server_available(), reason="Model service not active")
def test_ranking_personalization(dummy_image):
    user_id = "user_rank_test"
    item1_id = "test_item_green_1"
    
    # 1. Add item1 to VectorDB to ensure it has an embedding vector
    with dummy_image.open("rb") as fh:
        files = {'image': ('dummy.jpg', fh, 'image/jpeg')}
        requests.post(f"{MODEL_SERVICE_URL}/embeddings/add?item_id={item1_id}", files=files)
        
    # 2. Record an interaction with item1. This initializes the user profile.
    r = requests.post(f"{MODEL_SERVICE_URL}/ranking/interaction", json={
        "user_id": user_id,
        "item_id": item1_id,
        "weight": 1.0
    })
    assert r.status_code == 200
    
    # 3. Re-rank an arbitrary list of candidates where item1 is initially losing.
    candidates = [
        {"id": "some_other_item", "score": 0.6},
        {"id": item1_id, "score": 0.5}
    ]
    
    # Request a rank with a 50/50 blend between the original FAISS score and our personalization engine.
    r = requests.post(f"{MODEL_SERVICE_URL}/ranking/rank", json={
        "user_id": user_id,
        "candidates": candidates,
        "alpha": 0.5
    })
    
    assert r.status_code == 200
    results = r.json().get("results", [])
    
    assert len(results) == 2
    
    # Because the user explicitly interacted with item1, the personalization score should be ~1.0.
    # Its final score should be (0.5 * 0.5) + (0.5 * 1.0) = ~0.75.
    # "some_other_item" will remain roughly at 0.6 since we don't have a vector for it.
    # Therefore, item1 should be forcefully boosted to the top of the recommendation list!
    assert results[0]["id"] == item1_id
    assert results[0]["score"] > 0.6
    assert results[0]["personalization_score"] > 0.99
