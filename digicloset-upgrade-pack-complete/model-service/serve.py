from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uuid, os, shutil

app = FastAPI(title='DigiCloset Model Service (stub)')

@app.post('/predict')
async def predict(user_image: UploadFile = File(...), garment_image: UploadFile = File(None)):
    # This is a stub. Replace with real model loading and inference.
    job_id = uuid.uuid4().hex
    return {"job_id": job_id, "message": "prediction stub - implement model inference"}

@app.get('/')
def root():
    return {"message": "model service stub running"}
