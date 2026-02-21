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
def colorful_image(tmp_path):
    from PIL import Image
    img_path = tmp_path / "colorful.jpg"
    # Create an image that is 200x200
    # Background is white (imitating a product photo)
    # Foreground is a blue square taking up the center
    img = Image.new('RGB', (200, 200), color='white')
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    # Draw a blue garment in the middle
    d.rectangle([50, 50, 150, 150], fill='blue')
    img.save(img_path, format='JPEG')
    return img_path

@pytest.mark.skipif(not _server_available(), reason="Model service not active")
def test_color_extraction(colorful_image):
    with colorful_image.open("rb") as fh:
        files = {'image': ('colorful.jpg', fh, 'image/jpeg')}
        r = requests.post(f"{MODEL_SERVICE_URL}/colors/extract?num_colors=2", files=files, timeout=30)
    
    assert r.status_code == 200
    data = r.json()
    assert "colors" in data
    
    colors = data["colors"]
    # We requested 2 colors
    assert len(colors) == 2
    
    # Because of our background-removal heuristic, "Blue" should be detected as the dominant foreground color,
    # and "White" should be ignored or ranked much lower if detected at all.
    # The pure blue square should be easily identified as "Blue" from our custom FASHION_COLORS dictionary.
    top_color = colors[0]
    assert top_color["name"] == "Blue"
    assert top_color["percentage"] > 70.0  # It should make up the vast majority of the clustered foreground
