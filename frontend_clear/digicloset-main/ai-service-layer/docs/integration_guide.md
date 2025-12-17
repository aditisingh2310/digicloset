Integration Guide

1. Start AI microservice:
   cd ai_service
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app:app --reload --port 8000

2. From your backend, forward user images to http://localhost:8000/analyze
   - Keep HF_API_KEY secret on your backend; do not expose in client-side code.

3. For production, add authentication and rate-limiting, and run on GPU instances for performance.
