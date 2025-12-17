from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid, os, shutil

router = APIRouter()

class InferRequest(BaseModel):
    upload_id: str
    garment_id: str | None = None

# Placeholder: queue a job and return job id
JOB_DIR = '/tmp/digicloset_jobs'
os.makedirs(JOB_DIR, exist_ok=True)

@router.post('/', response_model=dict)
async def submit_infer(req: InferRequest):
    # In production: create DB job row + push to worker queue (Redis/Celery/RQ)
    jobid = uuid.uuid4().hex
    metadata = {"job_id": jobid, "upload_id": req.upload_id, "garment_id": req.garment_id}
    open(os.path.join(JOB_DIR, f"{jobid}.json"), 'w').write(str(metadata))
    # For skeleton, copy uploaded image as "result"
    # (Assumes upload path from uploads endpoint is accessible)
    return {"job_id": jobid, "status": "queued"}

@router.get('/{job_id}', response_model=dict)
async def get_status(job_id: str):
    f = os.path.join(JOB_DIR, f"{job_id}.json")
    if not os.path.exists(f):
        raise HTTPException(status_code=404, detail='Job not found')
    content = open(f).read()
    return {"job_id": job_id, "meta": content, "status": "queued"}
