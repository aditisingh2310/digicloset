# DEPRECATED: This backend is deprecated. It is not used by the Remix backend in /app. It must not be modified or extended.

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .routers import auth, uploads, infer, garments
from .middleware.security import InputSanitizationMiddleware

# ── Rate Limiter ──
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="DigiCloset Backend")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS (tightened) ──
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ── Input Sanitization ──
app.add_middleware(InputSanitizationMiddleware)

# ── Routers ──
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(uploads.router, prefix="/api/v1/uploads", tags=["uploads"])
app.include_router(infer.router, prefix="/api/v1/infer", tags=["infer"])
app.include_router(garments.router, prefix="/api/v1/garments", tags=["garments"])

@app.get("/")
async def root():
    return {"message": "DigiCloset backend - upgrade pack placeholder"}
