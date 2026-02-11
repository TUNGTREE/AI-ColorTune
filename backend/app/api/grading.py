"""Grading API endpoints - suggestions, preview, export."""
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.database import get_db
from app.config import settings
from app.core.color_params import ColorParams
from app.schemas.grading import (
    CreateTaskRequest,
    SuggestRequest,
    SelectSuggestionRequest,
    PreviewRequest,
    ExportRequest,
    SuggestionResponse,
    TaskResponse,
    ExportResponse,
)
from app.services.grading_service import GradingService
from app.api.ai_config import get_current_provider

router = APIRouter(prefix="/api/grading", tags=["grading"])


def _suggestion_response(s) -> SuggestionResponse:
    preview_url = None
    if s.preview_image_path:
        preview_url = f"/previews/{Path(s.preview_image_path).name}"
    return SuggestionResponse(
        id=s.id,
        suggestion_name=s.suggestion_name or "",
        parameters=s.parameters or {},
        preview_url=preview_url,
        is_selected=s.is_selected or False,
    )


def _task_response(task, suggestions=None) -> TaskResponse:
    original_url = None
    if task.original_image_path:
        original_url = f"/uploads/{Path(task.original_image_path).name}"
    return TaskResponse(
        id=task.id,
        user_id=task.user_id,
        profile_id=task.profile_id,
        original_image_url=original_url,
        status=task.status,
        suggestions=[_suggestion_response(s) for s in (suggestions or [])],
        created_at=task.created_at,
    )


# ------------------------------------------------------------------
# Task endpoints
# ------------------------------------------------------------------

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    profile_id: str = Form(None),
    db: Session = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type not allowed: {ext}")
    content = await file.read()
    file_id = str(uuid.uuid4())
    filepath = settings.UPLOAD_DIR / f"{file_id}.{ext}"
    filepath.write_bytes(content)

    svc = GradingService(db)
    task = svc.create_task(user_id, str(filepath), profile_id)
    return _task_response(task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    svc = GradingService(db)
    task = svc.get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    suggestions = svc.get_suggestions(task_id)
    return _task_response(task, suggestions)


# ------------------------------------------------------------------
# Suggestion endpoints
# ------------------------------------------------------------------

@router.post("/tasks/{task_id}/suggest", response_model=list[SuggestionResponse])
async def suggest(
    task_id: str,
    req: SuggestRequest = SuggestRequest(),
    db: Session = Depends(get_db),
):
    try:
        provider = get_current_provider()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"AI provider not available: {e}")

    svc = GradingService(db, provider)
    task = svc.get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    try:
        suggestions = await svc.generate_suggestions(task, req.num_suggestions)
    except Exception as e:
        logger.exception("Failed to generate suggestions for task %s", task_id)
        raise HTTPException(502, f"AI service error: {e}")
    return [_suggestion_response(s) for s in suggestions]


@router.get("/tasks/{task_id}/suggestions", response_model=list[SuggestionResponse])
def get_suggestions(task_id: str, db: Session = Depends(get_db)):
    svc = GradingService(db)
    suggestions = svc.get_suggestions(task_id)
    return [_suggestion_response(s) for s in suggestions]


@router.post("/suggestions/{suggestion_id}/select", response_model=SuggestionResponse)
def select_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
):
    svc = GradingService(db)
    suggestion = svc.db.get(
        __import__("app.models.grading", fromlist=["GradingSuggestion"]).GradingSuggestion,
        suggestion_id,
    )
    if suggestion is None:
        raise HTTPException(404, "Suggestion not found")
    try:
        result = svc.select_suggestion(suggestion.task_id, suggestion_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _suggestion_response(result)


# ------------------------------------------------------------------
# Preview endpoint
# ------------------------------------------------------------------

@router.post("/tasks/{task_id}/preview")
def preview(task_id: str, req: PreviewRequest, db: Session = Depends(get_db)):
    svc = GradingService(db)
    task = svc.get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    preview_url = svc.generate_preview(task, req.parameters)
    return {"preview_url": preview_url}


# ------------------------------------------------------------------
# Export endpoint
# ------------------------------------------------------------------

@router.post("/tasks/{task_id}/export", response_model=ExportResponse)
def export_image(task_id: str, req: ExportRequest, db: Session = Depends(get_db)):
    svc = GradingService(db)
    task = svc.get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    export = svc.export_image(task, req.parameters, req.format, req.quality)
    output_url = f"/exports/{Path(export.output_image_path).name}"
    return ExportResponse(
        id=export.id,
        task_id=export.task_id,
        output_url=output_url,
        export_format=export.export_format,
        quality=export.quality,
        created_at=export.created_at,
    )


@router.get("/exports/{export_id}/download")
def download_export(export_id: str, db: Session = Depends(get_db)):
    from app.models.grading import Export as ExportModel
    export = db.get(ExportModel, export_id)
    if export is None:
        raise HTTPException(404, "Export not found")
    return FileResponse(
        export.output_image_path,
        filename=f"colortune_{export_id}.{export.export_format}",
    )
