from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import aiofiles, os, uuid
from ..core import settings
from ..middleware.security import (
    validate_image_magic_bytes,
    validate_file_extension,
    validate_file_size,
    MAX_UPLOAD_SIZE_BYTES,
)

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/digicloset_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post('/', response_model=dict)
async def upload_image(file: UploadFile = File(...)):
    # 1. Validate extension
    validate_file_extension(file.filename)

    # 2. Validate declared content-type
    if file.content_type and file.content_type.split('/')[0] != 'image':
        raise HTTPException(status_code=400, detail='Only image uploads allowed')

    # 3. Read first chunk for magic byte validation
    first_chunk = await file.read(16)
    validate_image_magic_bytes(first_chunk, file.filename)

    # 4. Stream to disk with size enforcement
    ext = os.path.splitext(file.filename)[1]
    dest_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, dest_name)
    size = len(first_chunk)

    async with aiofiles.open(dest_path, 'wb') as out:
        await out.write(first_chunk)
        while content := await file.read(1024 * 1024):
            size += len(content)
            validate_file_size(size)
            await out.write(content)

    # 5. Send image to model-service for vector embedding
    try:
        import httpx
        embedding_url = os.getenv("EMBEDDING_ADD_URL", "http://model-service:8001/embeddings/add")
        async with aiofiles.open(dest_path, 'rb') as f:
            image_bytes = await f.read()

        async with httpx.AsyncClient() as client:
            files = {'image': (dest_name, image_bytes, file.content_type)}
            r = await client.post(f"{embedding_url}?item_id={dest_name}", files=files, timeout=10.0)
            if r.status_code != 200:
                print(f"Warning: Failed to generate embedding for {dest_name}: {r.text}")
    except Exception as e:
        print(f"Warning: Could not reach model-service for embedding: {str(e)}")

    return {"id": dest_name, "path": dest_path, "size": size}
