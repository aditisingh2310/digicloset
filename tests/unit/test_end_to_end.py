import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv('VITE_API_BASE_URL') or os.getenv('API_BASE_URL') or 'http://localhost:8000'

def test_health():
    # Backend has no /health, using root /
    r = requests.get(f"{API_BASE}/")
    print(f"Health check response: {r.status_code} {r.text}")
    assert r.status_code == 200

def test_tryon_flow():
    # 1. Upload Image
    print("Step 1: Uploading image...")
    files = {'file': ('sample.jpg', open('sample.jpg', 'rb'), 'image/jpeg')}
    r_upload = requests.post(f"{API_BASE}/api/v1/uploads/", files=files)
    print(f"Upload response: {r_upload.status_code} {r_upload.text}")
    assert r_upload.status_code == 200
    upload_data = r_upload.json()
    upload_id = upload_data.get('id')
    assert upload_id is not None
    print(f"Upload ID: {upload_id}")

    # 2. Submit Inference Job
    print("Step 2: Submitting inference job...")
    payload = {"upload_id": upload_id, "garment_id": "test_garment"}
    r_infer = requests.post(f"{API_BASE}/api/v1/infer/", json=payload)
    print(f"Infer response: {r_infer.status_code} {r_infer.text}")
    assert r_infer.status_code == 200
    infer_data = r_infer.json()
    job_id = infer_data.get('job_id')
    assert job_id is not None
    print(f"Job ID: {job_id}")

    # 3. Poll Job Status
    print("Step 3: Polling job status...")
    r_status = requests.get(f"{API_BASE}/api/v1/infer/{job_id}")
    print(f"Status response: {r_status.status_code} {r_status.text}")
    assert r_status.status_code == 200
    status_data = r_status.json()
    assert status_data.get('status') == 'queued'
    print("Job is queued as expected.")

if __name__ == "__main__":
    try:
        print(f"Running tests against {API_BASE}...")
        
        test_health()
        print("Health check passed!")
        
        # Create dummy sample.jpg if not exists
        if not os.path.exists('sample.jpg'):
            with open('sample.jpg', 'wb') as f:
                f.write(b'\xFF\xD8\xFF\xE0\x00\x10\x4A\x46\x49\x46\x00\x01') # minimal jpg header
        
        try:
            test_tryon_flow()
            print("Try-on flow passed!")
        except Exception as e:
            print(f"Try-on flow failed: {e}")
            raise e

        print("All tests passed!")
    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        exit(1)
