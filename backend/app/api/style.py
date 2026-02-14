"""Style discovery API endpoints."""
import logging
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.schemas.style import (
    CreateSessionRequest,
    SelectStyleRequest,
    StyleSessionResponse,
    StyleRoundResponse,
    StyleOptionResponse,
    UserProfileResponse,
)
from app.services.style_service import StyleService
from app.services.sample_scenes import get_sample_list, get_sample_image_path
from app.models.style import StyleRound
from app.api.ai_config import get_current_provider

import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/style", tags=["style"])


def _option_to_response(opt) -> StyleOptionResponse:
    preview_url = None
    if opt.preview_image_path:
        from pathlib import Path
        p = Path(opt.preview_image_path)
        preview_url = f"/previews/{p.name}"
    return StyleOptionResponse(
        id=opt.id,
        style_name=opt.style_name or "",
        parameters=opt.parameters or {},
        preview_url=preview_url,
        is_selected=opt.is_selected or False,
    )


def _round_to_response(rnd, options=None) -> StyleRoundResponse:
    original_url = None
    if rnd.original_image_path:
        from pathlib import Path
        p = Path(rnd.original_image_path)
        original_url = f"/uploads/{p.name}"
    return StyleRoundResponse(
        id=rnd.id,
        session_id=rnd.session_id,
        scene_type=rnd.scene_type,
        time_of_day=rnd.time_of_day,
        weather=rnd.weather,
        original_image_url=original_url,
        options=[_option_to_response(o) for o in (options or [])],
        created_at=rnd.created_at,
    )


# ------------------------------------------------------------------
# Sample endpoints
# ------------------------------------------------------------------

@router.get("/samples")
def list_samples():
    """Return available sample scenes for style discovery."""
    return get_sample_list()


class SampleRoundRequest(BaseModel):
    sample_id: str


@router.post("/sessions/{session_id}/rounds/sample", response_model=StyleRoundResponse)
async def create_round_from_sample(
    session_id: str,
    req: SampleRoundRequest,
    db: Session = Depends(get_db),
):
    """Create a style round using a sample image."""
    svc = StyleService(db)
    session = svc.get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")

    sample_path = get_sample_image_path(req.sample_id)
    if sample_path is None:
        raise HTTPException(400, f"Unknown sample: {req.sample_id}")

    # Copy sample to uploads directory
    file_id = str(uuid.uuid4())
    ext = sample_path.suffix.lstrip(".")
    dest = settings.UPLOAD_DIR / f"{file_id}.{ext}"
    shutil.copy2(str(sample_path), str(dest))

    # Find scene metadata
    sample_meta = None
    for s in get_sample_list():
        if s["id"] == req.sample_id:
            sample_meta = s
            break

    round_obj = svc.create_round(
        session_id,
        str(dest),
        scene_type=sample_meta["scene_type"] if sample_meta else None,
        time_of_day=sample_meta["time_of_day"] if sample_meta else None,
    )

    # Generate style options using AI
    try:
        ai = get_current_provider()
        svc.ai = ai
        options = await svc.generate_options_for_round(round_obj)
    except HTTPException:
        raise  # Re-raise HTTP errors (e.g. "API key not configured")
    except Exception as e:
        logger.exception("AI style generation failed for round %s", round_obj.id)
        raise HTTPException(502, f"AI service error: {e}")

    return _round_to_response(round_obj, options)


# ------------------------------------------------------------------
# Session endpoints
# ------------------------------------------------------------------

@router.post("/sessions", response_model=StyleSessionResponse)
def create_session(req: CreateSessionRequest, db: Session = Depends(get_db)):
    svc = StyleService(db)
    session = svc.create_session(req.user_id)
    return StyleSessionResponse(
        id=session.id,
        user_id=session.user_id,
        status=session.status,
        created_at=session.created_at,
    )


@router.get("/sessions/{session_id}", response_model=StyleSessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    svc = StyleService(db)
    session = svc.get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    rounds = svc.get_session_rounds(session_id)
    round_responses = []
    for r in rounds:
        options = svc.get_round_options(r.id)
        round_responses.append(_round_to_response(r, options))
    return StyleSessionResponse(
        id=session.id,
        user_id=session.user_id,
        status=session.status,
        rounds=round_responses,
        created_at=session.created_at,
    )


# ------------------------------------------------------------------
# Round endpoints
# ------------------------------------------------------------------

@router.post("/sessions/{session_id}/rounds", response_model=StyleRoundResponse)
async def create_round(
    session_id: str,
    file: UploadFile = File(...),
    scene_type: str | None = Form(None),
    time_of_day: str | None = Form(None),
    weather: str | None = Form(None),
    db: Session = Depends(get_db),
):
    svc = StyleService(db)
    session = svc.get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")

    # Save uploaded image
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type not allowed: {ext}")
    content = await file.read()
    file_id = str(uuid.uuid4())
    filepath = settings.UPLOAD_DIR / f"{file_id}.{ext}"
    filepath.write_bytes(content)

    round_obj = svc.create_round(
        session_id, str(filepath), scene_type, time_of_day, weather
    )

    # Generate style options using AI
    try:
        ai = get_current_provider()
        svc.ai = ai
        options = await svc.generate_options_for_round(round_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("AI style generation failed for round %s", round_obj.id)
        raise HTTPException(502, f"AI service error: {e}")

    return _round_to_response(round_obj, options)


@router.get("/rounds/{round_id}/options", response_model=list[StyleOptionResponse])
def get_round_options(round_id: str, db: Session = Depends(get_db)):
    svc = StyleService(db)
    options = svc.get_round_options(round_id)
    return [_option_to_response(o) for o in options]


@router.post("/rounds/{round_id}/regenerate", response_model=StyleRoundResponse)
async def regenerate_options(round_id: str, db: Session = Depends(get_db)):
    """Delete existing options for a round and regenerate new ones."""
    svc = StyleService(db)
    round_obj = db.get(StyleRound, round_id)
    if round_obj is None:
        raise HTTPException(404, "Round not found")

    # Delete old options
    from app.models.style import StyleOption as StyleOptionModel
    db.query(StyleOptionModel).filter(StyleOptionModel.round_id == round_id).delete()
    db.commit()

    # Regenerate
    try:
        ai = get_current_provider()
        svc.ai = ai
        options = await svc.generate_options_for_round(round_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("AI style regeneration failed for round %s", round_id)
        raise HTTPException(502, f"AI service error: {e}")

    return _round_to_response(round_obj, options)


@router.post("/rounds/{round_id}/select", response_model=StyleOptionResponse)
def select_style(round_id: str, req: SelectStyleRequest, db: Session = Depends(get_db)):
    svc = StyleService(db)
    try:
        option = svc.select_option(round_id, req.option_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _option_to_response(option)


# ------------------------------------------------------------------
# Analysis endpoint
# ------------------------------------------------------------------

@router.post("/sessions/{session_id}/analyze", response_model=UserProfileResponse)
async def analyze_session(session_id: str, db: Session = Depends(get_db)):
    ai = get_current_provider()
    svc = StyleService(db, ai)
    try:
        profile = await svc.analyze_preferences(session_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return UserProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        session_id=profile.session_id,
        profile_data=profile.profile_data,
        created_at=profile.created_at,
    )


@router.get("/profiles/{profile_id}", response_model=UserProfileResponse)
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    svc = StyleService(db)
    profile = svc.get_profile(profile_id)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    return UserProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        session_id=profile.session_id,
        profile_data=profile.profile_data,
        created_at=profile.created_at,
    )
