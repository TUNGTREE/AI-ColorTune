"""Pydantic schemas for style discovery API."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.color_params import ColorParams


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    user_id: str | None = None  # auto-create user if None


class CreateRoundRequest(BaseModel):
    scene_type: str | None = None
    time_of_day: str | None = None
    weather: str | None = None


class SelectStyleRequest(BaseModel):
    option_id: str


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class StyleOptionResponse(BaseModel):
    id: str
    style_name: str
    description: str = ""
    parameters: dict
    preview_url: str | None = None
    is_selected: bool = False


class StyleRoundResponse(BaseModel):
    id: str
    session_id: str
    scene_type: str | None
    time_of_day: str | None
    weather: str | None
    original_image_url: str | None
    options: list[StyleOptionResponse] = []
    created_at: datetime | None = None


class StyleSessionResponse(BaseModel):
    id: str
    user_id: str
    status: str
    rounds: list[StyleRoundResponse] = []
    created_at: datetime | None = None


class UserProfileResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    profile_data: dict
    created_at: datetime | None = None
