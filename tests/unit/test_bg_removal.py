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
    from PIL import Image, ImageDraw
    # Create an image that is 100x100
    # Background is Red
    # Foreground is a Green square in the center
    img = Image.new('RGB', (100, 100), color='red')
    d = ImageDraw.Draw(img)
    d.rectangle([25, 25, 75, 75], fill='green')
    
    img_path = tmp_path / "dummy_rgb.jpg"
    img.save(img_path, format='JPEG')
    return img_path

@pytest.mark.skipif(not _server_available(), reason="Model service not active")
def test_bg_removal_transparent(dummy_image):
    """Test generating a transparent PNG"""
    with dummy_image.open("rb") as fh:
        files = {'image': ('dummy_rgb.jpg', fh, 'image/jpeg')}
        # Don't pass bg_color, should return a transparent PNG
        r = requests.post(f"{MODEL_SERVICE_URL}/images/remove-bg", files=files, timeout=180)
        
    assert r.status_code == 200
    assert r.headers['Content-Type'] == "image/png"
    
    # Verify image properties
    from PIL import Image
    import io
    output_img = Image.open(io.BytesIO(r.content))
    assert output_img.mode == "RGBA"
    
    # Check that corners (which were red) are now transparent (alpha=0)
    # Note: rembg might leave slight edge artifacts, but true corners should be 0.
    pixels = output_img.load()
    assert pixels[0, 0][3] == 0
    assert pixels[99, 99][3] == 0

@pytest.mark.skipif(not _server_available(), reason="Model service not active")
def test_bg_removal_solid_color(dummy_image):
    """Test replacing the background with a specific hex color (e.g., white #FFFFFF)"""
    with dummy_image.open("rb") as fh:
        files = {'image': ('dummy_rgb.jpg', fh, 'image/jpeg')}
        # Pass bg_color='#FFFFFF', should return a JPEG composite
        r = requests.post(f"{MODEL_SERVICE_URL}/images/remove-bg?bg_color=%23FFFFFF", files=files, timeout=180)
        
    assert r.status_code == 200
    assert r.headers['Content-Type'] == "image/jpeg"
    
    from PIL import Image
    import io
    output_img = Image.open(io.BytesIO(r.content))
    assert output_img.mode == "RGB"
    
    # Check that corners (which were red) are now white (255, 255, 255)
    pixels = output_img.load()
    assert pixels[0, 0] == (255, 255, 255)
    assert pixels[99, 99] == (255, 255, 255)
