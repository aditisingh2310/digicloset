DigiCloset AI Microservice
==========================

Overview
--------
This FastAPI microservice provides image analysis to support virtual try-on features.
- Uses local PyTorch segmentation if available for higher-quality per-image analysis.
- Optionally calls the Hugging Face Inference API when HF_API_KEY is provided.
- Falls back to fast heuristics when neither is available.

Endpoints
---------
- GET /health -> service info
- POST /analyze -> multipart form upload (file field), returns JSON

Running locally
---------------
1. Create and activate a venv
   python -m venv venv
   source venv/bin/activate
2. Install base requirements
   pip install -r requirements.txt
3. Run:
   uvicorn app:app --reload --port 8000

To enable local PyTorch model inference, install torch & torchvision (see requirements-torch.txt).
To enable Hugging Face, set HF_API_KEY environment variable.
