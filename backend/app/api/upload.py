import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings

router = APIRouter()


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # Validate extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB",
        )

    # Save file
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{ext}"
    filepath = settings.UPLOAD_DIR / filename
    filepath.write_bytes(content)

    return {"id": file_id, "filename": filename, "size": len(content)}
