"""Tests for Grading Suggestions (Phase 4).

Tests task creation, AI-based suggestion generation, selection, preview, and
personalization based on different user profiles.
"""
import json
import struct
import uuid
import zlib
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import Base, engine, SessionLocal
from app.core.color_params import ColorParams, BasicParams, ColorAdjustParams, EffectsParams
from app.services.grading_service import GradingService
from app.models.user import User
from app.models.style import UserStyleProfile


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
    sig = b"\x89PNG\r\n\x1a\n"
    def chunk(ctype, data):
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc
    ihdr = struct.pack(">IIBBBBB", 10, 10, 8, 2, 0, 0, 0)
    raw_data = b""
    for _ in range(10):
        raw_data += b"\x00" + b"\x80\x60\x40" * 10
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw_data)) + chunk(b"IEND", b"")


def make_warm_suggestions():
    """Suggestions tailored for a warm-style profile."""
    return [
        {
            "suggestion_name": "Golden Warmth",
            "description": "Warm golden tones matching user preference",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.3, contrast=20, shadows=15),
                color=ColorAdjustParams(temperature=7500, vibrance=15, saturation=10),
                effects=EffectsParams(clarity=15, vignette=-15),
            ).model_dump(),
        },
        {
            "suggestion_name": "Amber Sunset",
            "description": "Deep amber tones with rich shadows",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.1, contrast=30, highlights=-20, shadows=10),
                color=ColorAdjustParams(temperature=8000, tint=5, vibrance=20, saturation=15),
                effects=EffectsParams(clarity=20, vignette=-25, grain=5),
            ).model_dump(),
        },
        {
            "suggestion_name": "Soft Honey",
            "description": "Soft warm tones with lifted shadows",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.5, contrast=-10, shadows=30),
                color=ColorAdjustParams(temperature=7200, vibrance=10, saturation=-5),
                effects=EffectsParams(clarity=10),
            ).model_dump(),
        },
    ]


def make_cool_suggestions():
    """Suggestions tailored for a cool-style profile."""
    return [
        {
            "suggestion_name": "Arctic Blue",
            "description": "Cool blue tones for moody look",
            "parameters": ColorParams(
                basic=BasicParams(exposure=-0.2, contrast=35, highlights=-15),
                color=ColorAdjustParams(temperature=4500, vibrance=10, saturation=5),
                effects=EffectsParams(clarity=25, vignette=-30),
            ).model_dump(),
        },
        {
            "suggestion_name": "Steel Gray",
            "description": "Desaturated cool tones",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.0, contrast=20),
                color=ColorAdjustParams(temperature=5000, saturation=-20, vibrance=-5),
                effects=EffectsParams(clarity=20, grain=10),
            ).model_dump(),
        },
        {
            "suggestion_name": "Teal Shadow",
            "description": "Teal-tinted shadows with neutral highlights",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.1, contrast=25, shadows=-10),
                color=ColorAdjustParams(temperature=5500, tint=-10, vibrance=15),
                effects=EffectsParams(clarity=15, dehaze=10),
            ).model_dump(),
        },
    ]


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

class TestGradingServiceDirect:
    def test_create_task(self, db):
        user = User(id="user-1")
        db.add(user)
        db.commit()

        svc = GradingService(db)
        # Need a real image file
        from app.config import settings
        import numpy as np
        from PIL import Image
        img_path = settings.UPLOAD_DIR / "test_grading.png"
        Image.fromarray(np.full((10, 10, 3), 128, dtype=np.uint8)).save(img_path)

        task = svc.create_task("user-1", str(img_path))
        assert task.status == "uploaded"
        assert task.user_id == "user-1"

    def test_generate_preview(self, db):
        user = User(id="user-1")
        db.add(user)
        db.commit()

        from app.config import settings
        import numpy as np
        from PIL import Image
        img_path = settings.UPLOAD_DIR / "test_preview.png"
        Image.fromarray(np.full((100, 100, 3), 128, dtype=np.uint8)).save(img_path)

        svc = GradingService(db)
        task = svc.create_task("user-1", str(img_path))
        params = ColorParams(basic=BasicParams(exposure=0.5, contrast=20))
        preview_url = svc.generate_preview(task, params)
        assert preview_url.startswith("/previews/")
        assert preview_url.endswith(".jpg")


# ---------------------------------------------------------------------------
# Personalization test
# ---------------------------------------------------------------------------

class TestPersonalization:
    def test_warm_vs_cool_suggestions_differ(self):
        """Suggestions for different profiles should differ."""
        warm = make_warm_suggestions()
        cool = make_cool_suggestions()

        warm_temps = [ColorParams(**s["parameters"]).color.temperature for s in warm]
        cool_temps = [ColorParams(**s["parameters"]).color.temperature for s in cool]

        avg_warm = sum(warm_temps) / len(warm_temps)
        avg_cool = sum(cool_temps) / len(cool_temps)
        assert avg_warm > avg_cool + 1000, "Warm suggestions should have higher temperature"

    def test_suggestions_have_different_params(self):
        """Each suggestion within a set should differ."""
        suggestions = make_warm_suggestions()
        params_list = [ColorParams(**s["parameters"]) for s in suggestions]

        # At least contrast should vary
        contrasts = [p.basic.contrast for p in params_list]
        assert len(set(contrasts)) >= 2, "Suggestions should have varying contrast"

        # Names should be unique
        names = [s["suggestion_name"] for s in suggestions]
        assert len(set(names)) == len(names)


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_api(client):
    # First create a user via style session
    resp = await client.post("/api/style/sessions", json={})
    user_id = resp.json()["user_id"]

    png_data = make_test_png()
    resp = await client.post(
        "/api/grading/tasks",
        data={"user_id": user_id},
        files={"file": ("test.png", png_data, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "uploaded"
    assert data["user_id"] == user_id


@pytest.mark.asyncio
async def test_full_grading_flow_api(client):
    """Full flow: create task → generate suggestions → select → preview."""
    # Setup user
    resp = await client.post("/api/style/sessions", json={})
    user_id = resp.json()["user_id"]

    # Create task
    png_data = make_test_png()
    resp = await client.post(
        "/api/grading/tasks",
        data={"user_id": user_id},
        files={"file": ("test.png", png_data, "image/png")},
    )
    task_id = resp.json()["id"]

    # Mock AI for suggestions
    mock_ai = AsyncMock()
    mock_ai.generate_grading_suggestions = AsyncMock(return_value=make_warm_suggestions())

    with patch("app.api.grading.get_current_provider", return_value=mock_ai):
        # Generate suggestions
        resp = await client.post(f"/api/grading/tasks/{task_id}/suggest")
        assert resp.status_code == 200
        suggestions = resp.json()
        assert len(suggestions) == 3
        assert all("preview_url" in s for s in suggestions)

    # Get suggestions
    resp = await client.get(f"/api/grading/tasks/{task_id}/suggestions")
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    # Get task with suggestions
    resp = await client.get(f"/api/grading/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "suggested"
    assert len(resp.json()["suggestions"]) == 3

    # Select a suggestion
    suggestion_id = suggestions[0]["id"]
    resp = await client.post(f"/api/grading/suggestions/{suggestion_id}/select")
    assert resp.status_code == 200
    assert resp.json()["is_selected"] is True

    # Generate custom preview
    params = ColorParams(basic=BasicParams(exposure=0.5, contrast=30))
    resp = await client.post(
        f"/api/grading/tasks/{task_id}/preview",
        json={"parameters": params.model_dump()},
    )
    assert resp.status_code == 200
    assert "preview_url" in resp.json()


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    resp = await client.get("/api/grading/tasks/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_preview_with_various_params(client):
    """Preview endpoint handles diverse parameter combinations."""
    resp = await client.post("/api/style/sessions", json={})
    user_id = resp.json()["user_id"]

    png_data = make_test_png()
    resp = await client.post(
        "/api/grading/tasks",
        data={"user_id": user_id},
        files={"file": ("test.png", png_data, "image/png")},
    )
    task_id = resp.json()["id"]

    # Test with various parameter sets
    test_params = [
        ColorParams(),  # Identity
        ColorParams(basic=BasicParams(exposure=2.0, contrast=80)),  # Extreme bright
        ColorParams(basic=BasicParams(exposure=-2.0), color=ColorAdjustParams(temperature=3000)),  # Dark cool
    ]
    for params in test_params:
        resp = await client.post(
            f"/api/grading/tasks/{task_id}/preview",
            json={"parameters": params.model_dump()},
        )
        assert resp.status_code == 200
        assert resp.json()["preview_url"].startswith("/previews/")
