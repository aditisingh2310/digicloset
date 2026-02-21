# DEPRECATED: This backend is deprecated. It is not used by the Remix backend in /app. It must not be modified or extended.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, uploads, infer, garments

app = FastAPI(title="DigiCloset Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(uploads.router, prefix="/api/v1/uploads", tags=["uploads"])
app.include_router(infer.router, prefix="/api/v1/infer", tags=["infer"])
app.include_router(garments.router, prefix="/api/v1/garments", tags=["garments"])

@app.get("/")
async def root():
    return {"message": "DigiCloset backend - upgrade pack placeholder"}
