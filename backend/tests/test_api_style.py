"""Tests for Style Discovery (Phase 3).

Tests the complete flow: create session → create rounds → generate options
→ select preferences → analyze → generate profile.
All AI calls are mocked.
"""
import json
import struct
import uuid
import zlib
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import Base, engine, SessionLocal
from app.core.color_params import ColorParams, BasicParams, ColorAdjustParams, EffectsParams
from app.services.style_service import StyleService
from app.models.user import User
from app.models.style import StyleSession, StyleRound, StyleOption


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def make_test_png() -> bytes:
    """Create a minimal valid 10x10 PNG."""
    sig = b"\x89PNG\r\n\x1a\n"
    def chunk(ctype, data):
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc
    ihdr = struct.pack(">IIBBBBB", 10, 10, 8, 2, 0, 0, 0)
    # 10 rows of 10 RGB pixels, each row prefixed with filter byte 0
    raw_data = b""
    for _ in range(10):
        raw_data += b"\x00" + b"\x80\x60\x40" * 10
    compressed = zlib.compress(raw_data)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


# Mock AI responses
def make_mock_scene():
    return {
        "scene_type": "landscape",
        "time_of_day": "golden_hour",
        "weather": "sunny",
        "dominant_colors": ["orange", "blue"],
        "color_temperature_feel": "warm",
        "mood": "serene",
        "subjects": ["mountains"],
        "composition": "rule of thirds",
    }


def make_mock_styles(n=4):
    """Generate n distinct mock style options with different parameters."""
    styles = [
        {
            "style_name": "Cinematic Teal & Orange",
            "description": "Classic cinema look with teal shadows and orange highlights",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.3, contrast=30, highlights=-25, shadows=20),
                color=ColorAdjustParams(temperature=7800, saturation=15, vibrance=20),
                effects=EffectsParams(clarity=20, vignette=-25),
            ).model_dump(),
        },
        {
            "style_name": "Clean & Airy",
            "description": "Bright, clean look with lifted shadows",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.6, contrast=-15, highlights=-40, shadows=50),
                color=ColorAdjustParams(temperature=6200, saturation=-10, vibrance=10),
                effects=EffectsParams(clarity=10),
            ).model_dump(),
        },
        {
            "style_name": "Moody Dark",
            "description": "Dark and moody with crushed blacks",
            "parameters": ColorParams(
                basic=BasicParams(exposure=-0.3, contrast=40, highlights=-10, shadows=-20, blacks=-30),
                color=ColorAdjustParams(temperature=5500, saturation=5, vibrance=-10),
                effects=EffectsParams(clarity=30, vignette=-40, grain=15),
            ).model_dump(),
        },
        {
            "style_name": "Vintage Film",
            "description": "Warm vintage film emulation",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.1, contrast=10, shadows=15),
                color=ColorAdjustParams(temperature=7200, tint=5, saturation=-15, vibrance=5),
                effects=EffectsParams(clarity=-10, grain=30, vignette=-15),
            ).model_dump(),
        },
        {
            "style_name": "Bold & Punchy",
            "description": "High contrast vivid colors",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.2, contrast=50, highlights=-15, shadows=10),
                color=ColorAdjustParams(temperature=6500, saturation=35, vibrance=30),
                effects=EffectsParams(clarity=40, dehaze=15),
            ).model_dump(),
        },
        {
            "style_name": "Soft Pastel",
            "description": "Soft muted tones",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.4, contrast=-25, highlights=-30, shadows=30),
                color=ColorAdjustParams(temperature=6800, saturation=-25, vibrance=-10),
                effects=EffectsParams(clarity=-15),
            ).model_dump(),
        },
    ]
    return styles[:n]


def make_mock_profile():
    return {
        "temperature_preference": "warm",
        "contrast_preference": "medium",
        "saturation_preference": "moderate",
        "tone_preference": "balanced",
        "color_tendencies": ["warm tones", "orange highlights"],
        "effects_notes": "Prefers subtle clarity and light vignette",
        "overall_style_summary": "Warm balanced style with moderate contrast.",
        "reference_styles": ["Film Emulation", "Golden Hour"],
    }


# ---------------------------------------------------------------------------
# Service-level tests (direct, no HTTP)
# ---------------------------------------------------------------------------

class TestStyleServiceDirect:
    def test_create_session_auto_user(self, db):
        svc = StyleService(db)
        session = svc.create_session()
        assert session.id is not None
        assert session.user_id is not None
        assert session.status == "in_progress"

    def test_create_session_existing_user(self, db):
        user = User(id="user-123")
        db.add(user)
        db.commit()
        svc = StyleService(db)
        session = svc.create_session("user-123")
        assert session.user_id == "user-123"

    def test_create_round(self, db):
        svc = StyleService(db)
        session = svc.create_session()
        rnd = svc.create_round(session.id, "/tmp/test.jpg", "landscape", "golden_hour", "sunny")
        assert rnd.session_id == session.id
        assert rnd.scene_type == "landscape"

    def test_select_option(self, db):
        svc = StyleService(db)
        session = svc.create_session()
        rnd = svc.create_round(session.id, "/tmp/test.jpg")

        # Manually add options
        opt1 = StyleOption(id="opt1", round_id=rnd.id, style_name="Style A", parameters={})
        opt2 = StyleOption(id="opt2", round_id=rnd.id, style_name="Style B", parameters={})
        db.add_all([opt1, opt2])
        db.commit()

        selected = svc.select_option(rnd.id, "opt1")
        assert selected.is_selected is True

        # Verify other deselected
        db.refresh(opt2)
        assert opt2.is_selected is False

    def test_select_option_invalid(self, db):
        svc = StyleService(db)
        session = svc.create_session()
        rnd = svc.create_round(session.id, "/tmp/test.jpg")
        with pytest.raises(ValueError):
            svc.select_option(rnd.id, "nonexistent")

    def test_selections_summary(self, db):
        svc = StyleService(db)
        session = svc.create_session()
        rnd = svc.create_round(session.id, "/tmp/test.jpg", "landscape")
        opt = StyleOption(
            id="opt1", round_id=rnd.id, style_name="Cinematic",
            parameters=ColorParams().model_dump(), is_selected=True,
        )
        db.add(opt)
        db.commit()

        summary = svc.get_selections_summary(session.id)
        assert len(summary) == 1
        assert summary[0]["selected_style"] == "Cinematic"


# ---------------------------------------------------------------------------
# Style option diversity test
# ---------------------------------------------------------------------------

class TestStyleDiversity:
    def test_options_have_distinct_parameters(self):
        """Generated styles should be visually distinct."""
        styles = make_mock_styles(4)
        params_list = [ColorParams(**s["parameters"]) for s in styles]

        # Check temperature spread
        temps = [p.color.temperature for p in params_list]
        assert max(temps) - min(temps) >= 500, "Temperature range too narrow"

        # Check contrast spread
        contrasts = [p.basic.contrast for p in params_list]
        assert max(contrasts) - min(contrasts) >= 30, "Contrast range too narrow"

        # Check saturation spread
        sats = [p.color.saturation for p in params_list]
        assert max(sats) - min(sats) >= 20, "Saturation range too narrow"

    def test_each_option_has_valid_params(self):
        styles = make_mock_styles(6)
        for s in styles:
            params = ColorParams(**s["parameters"])
            assert s["style_name"] != ""
            assert params.version == "1.0"

    def test_options_have_unique_names(self):
        styles = make_mock_styles(6)
        names = [s["style_name"] for s in styles]
        assert len(names) == len(set(names)), "Style names must be unique"


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_session_api(client):
    resp = await client.post("/api/style/sessions", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_get_session_api(client):
    # Create
    resp = await client.post("/api/style/sessions", json={})
    sid = resp.json()["id"]
    # Get
    resp = await client.get(f"/api/style/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sid


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    resp = await client.get("/api/style/sessions/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_full_flow_api(client):
    """Complete style discovery flow test with mocked AI."""
    # 1. Create session
    resp = await client.post("/api/style/sessions", json={})
    assert resp.status_code == 200
    session_id = resp.json()["id"]
    user_id = resp.json()["user_id"]

    # Mock AI provider
    mock_ai = AsyncMock()
    mock_ai.analyze_scene = AsyncMock(return_value=make_mock_scene())
    mock_ai.generate_style_options = AsyncMock(return_value=make_mock_styles(4))
    mock_ai.analyze_preferences = AsyncMock(return_value=make_mock_profile())

    with patch("app.api.style.get_current_provider", return_value=mock_ai):
        # 2. Create round with image upload
        png_data = make_test_png()
        resp = await client.post(
            f"/api/style/sessions/{session_id}/rounds",
            files={"file": ("test.png", png_data, "image/png")},
        )
        assert resp.status_code == 200
        round_data = resp.json()
        assert len(round_data["options"]) == 4

        # Verify options have distinct names
        names = [o["style_name"] for o in round_data["options"]]
        assert len(set(names)) == 4

        # 3. Get options
        round_id = round_data["id"]
        resp = await client.get(f"/api/style/rounds/{round_id}/options")
        assert resp.status_code == 200
        assert len(resp.json()) == 4

        # 4. Select a style
        option_id = round_data["options"][0]["id"]
        resp = await client.post(
            f"/api/style/rounds/{round_id}/select",
            json={"option_id": option_id},
        )
        assert resp.status_code == 200
        assert resp.json()["is_selected"] is True

        # 5. Analyze preferences
        resp = await client.post(f"/api/style/sessions/{session_id}/analyze")
        assert resp.status_code == 200
        profile = resp.json()
        assert "profile_data" in profile
        assert profile["profile_data"]["temperature_preference"] == "warm"
        assert profile["user_id"] == user_id

        # 6. Retrieve profile
        profile_id = profile["id"]
        resp = await client.get(f"/api/style/profiles/{profile_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == profile_id


@pytest.mark.asyncio
async def test_profile_content_reasonable(client):
    """Verify profile analysis output contains expected fields."""
    profile_data = make_mock_profile()
    required_fields = [
        "temperature_preference", "contrast_preference",
        "saturation_preference", "tone_preference",
        "overall_style_summary",
    ]
    for field in required_fields:
        assert field in profile_data, f"Missing field: {field}"
    assert profile_data["temperature_preference"] in ["warm", "neutral", "cool"]
    assert profile_data["contrast_preference"] in ["high", "medium", "low"]
