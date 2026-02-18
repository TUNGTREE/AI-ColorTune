"""Pydantic schemas for grading API."""
from datetime import datetime

from pydantic import BaseModel

from app.core.color_params import ColorParams


class CreateTaskRequest(BaseModel):
    user_id: str
    profile_id: str | None = None


class SuggestRequest(BaseModel):
    num_suggestions: int = 3
    custom_prompt: str | None = None


class SelectSuggestionRequest(BaseModel):
    suggestion_id: str


class PreviewRequest(BaseModel):
    parameters: ColorParams


class ExportRequest(BaseModel):
    parameters: ColorParams
    format: str = "jpeg"
    quality: int = 95


class SuggestionResponse(BaseModel):
    id: str
    suggestion_name: str
    description: str = ""
    parameters: dict
    preview_url: str | None = None
    is_selected: bool = False


class TaskResponse(BaseModel):
    id: str
    user_id: str
    profile_id: str | None
    original_image_url: str | None
    status: str
    suggestions: list[SuggestionResponse] = []
    created_at: datetime | None = None


class ExportResponse(BaseModel):
    id: str
    task_id: str
    output_url: str | None
    export_format: str
    quality: int
    created_at: datetime | None = None
