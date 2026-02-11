"""End-to-end integration tests (Phase 7).

Full user journey: style discovery → grading suggestions → preview → export.
"""
import struct
import zlib
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import Base, engine
from app.core.color_params import (
    ColorParams, BasicParams, ColorAdjustParams, EffectsParams,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def make_test_png(width=10, height=10, pixel=b"\x80\x60\x40") -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    def chunk(ctype, data):
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_data = b""
    for _ in range(height):
        raw_data += b"\x00" + pixel * width
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw_data)) + chunk(b"IEND", b"")


def _mock_style_options():
    return [
        {
            "style_name": "Cinematic",
            "description": "Bold cinematic look",
            "scene_analysis": {"scene_type": "landscape"},
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.2, contrast=30),
                color=ColorAdjustParams(temperature=7000, vibrance=15),
                effects=EffectsParams(clarity=20, vignette=-20),
            ).model_dump(),
        },
        {
            "style_name": "Vintage",
            "description": "Faded vintage feel",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.1, contrast=-10, shadows=20),
                color=ColorAdjustParams(temperature=7500, saturation=-15),
                effects=EffectsParams(grain=15),
            ).model_dump(),
        },
        {
            "style_name": "Clean",
            "description": "Bright and clean",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.4, contrast=10, highlights=-10),
                color=ColorAdjustParams(vibrance=10),
            ).model_dump(),
        },
        {
            "style_name": "Moody",
            "description": "Dark and moody",
            "parameters": ColorParams(
                basic=BasicParams(exposure=-0.3, contrast=40),
                color=ColorAdjustParams(temperature=5500, saturation=-10),
                effects=EffectsParams(clarity=30, vignette=-40),
            ).model_dump(),
        },
    ]


def _mock_grading_suggestions():
    return [
        {
            "suggestion_name": "Warm Cinematic",
            "description": "Warm tones with cinematic contrast",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.3, contrast=25, shadows=10),
                color=ColorAdjustParams(temperature=7200, vibrance=20),
                effects=EffectsParams(clarity=15, vignette=-15),
            ).model_dump(),
        },
        {
            "suggestion_name": "Natural Warmth",
            "description": "Subtly enhanced natural look",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.1, contrast=10),
                color=ColorAdjustParams(temperature=6800, vibrance=10),
            ).model_dump(),
        },
        {
            "suggestion_name": "Golden Hour",
            "description": "Golden tones like sunset light",
            "parameters": ColorParams(
                basic=BasicParams(exposure=0.5, contrast=15, highlights=-15),
                color=ColorAdjustParams(temperature=8000, vibrance=25, saturation=10),
                effects=EffectsParams(clarity=10),
            ).model_dump(),
        },
    ]


# ---------------------------------------------------------------------------
# Full E2E test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_user_journey(client):
    """
    Complete user journey:
    1. Create style session
    2. Upload photos → get style options → make selections (3 rounds)
    3. Analyze preferences → get style profile
    4. Create grading task with new photo
    5. Generate suggestions based on profile
    6. Select suggestion
    7. Preview with custom params
    8. Export final image
    """

    # -- Step 1: Create style discovery session --
    mock_ai = AsyncMock()
    mock_ai.analyze_scene = AsyncMock(return_value={
        "scene_type": "landscape",
        "time_of_day": "golden_hour",
        "weather": "sunny",
    })
    mock_ai.generate_style_options = AsyncMock(return_value=_mock_style_options())
    mock_ai.analyze_preferences = AsyncMock(return_value={
        "overall_style": "warm cinematic",
        "preferred_temperature": "warm (7000-8000K)",
        "contrast_preference": "medium-high",
        "saturation_preference": "slightly boosted",
        "typical_adjustments": {
            "exposure": "+0.1 to +0.3",
            "contrast": "+20 to +35",
            "temperature": "7000-8000K",
        },
    })
    mock_ai.generate_grading_suggestions = AsyncMock(
        return_value=_mock_grading_suggestions()
    )

    with patch("app.api.style.get_current_provider", return_value=mock_ai), \
         patch("app.api.grading.get_current_provider", return_value=mock_ai):

        # Create session
        resp = await client.post("/api/style/sessions", json={})
        assert resp.status_code == 200
        session = resp.json()
        session_id = session["id"]
        user_id = session["user_id"]

        # -- Step 2: 3 rounds of style discovery --
        selected_options = []
        for round_num in range(3):
            png_data = make_test_png(
                pixel=bytes([60 + round_num * 30, 80 + round_num * 20, 100 + round_num * 10])
            )
            resp = await client.post(
                f"/api/style/sessions/{session_id}/rounds",
                files={"file": (f"test_{round_num}.png", png_data, "image/png")},
            )
            assert resp.status_code == 200
            round_data = resp.json()
            assert len(round_data["options"]) >= 3

            # Select first option in each round
            option = round_data["options"][0]
            resp = await client.post(
                f"/api/style/rounds/{round_data['id']}/select",
                json={"option_id": option["id"]},
            )
            assert resp.status_code == 200
            selected_options.append(option)

        # -- Step 3: Analyze preferences --
        resp = await client.post(f"/api/style/sessions/{session_id}/analyze")
        assert resp.status_code == 200
        profile = resp.json()
        profile_id = profile["id"]
        assert profile["profile_data"] is not None

        # Verify session is completed
        resp = await client.get(f"/api/style/sessions/{session_id}")
        assert resp.json()["status"] == "completed"

        # -- Step 4: Create grading task --
        png_data = make_test_png(pixel=b"\xa0\x80\x60")
        resp = await client.post(
            "/api/grading/tasks",
            data={"user_id": user_id, "profile_id": profile_id},
            files={"file": ("photo.png", png_data, "image/png")},
        )
        assert resp.status_code == 200
        task = resp.json()
        task_id = task["id"]
        assert task["status"] == "uploaded"
        assert task["profile_id"] == profile_id

        # -- Step 5: Generate suggestions --
        resp = await client.post(f"/api/grading/tasks/{task_id}/suggest")
        assert resp.status_code == 200
        suggestions = resp.json()
        assert len(suggestions) == 3
        assert all(s["preview_url"] for s in suggestions)

        # -- Step 6: Select a suggestion --
        chosen = suggestions[0]
        resp = await client.post(f"/api/grading/suggestions/{chosen['id']}/select")
        assert resp.status_code == 200
        assert resp.json()["is_selected"] is True

        # Verify task status updated
        resp = await client.get(f"/api/grading/tasks/{task_id}")
        assert resp.json()["status"] == "tuning"

    # -- Step 7: Preview with custom tweaks (no AI needed) --
    custom_params = ColorParams(
        basic=BasicParams(exposure=0.4, contrast=30, shadows=15),
        color=ColorAdjustParams(temperature=7500, vibrance=25),
        effects=EffectsParams(clarity=20, vignette=-20),
    )
    resp = await client.post(
        f"/api/grading/tasks/{task_id}/preview",
        json={"parameters": custom_params.model_dump()},
    )
    assert resp.status_code == 200
    assert resp.json()["preview_url"].startswith("/previews/")

    # -- Step 8: Export final image --
    resp = await client.post(
        f"/api/grading/tasks/{task_id}/export",
        json={
            "parameters": custom_params.model_dump(),
            "format": "jpeg",
            "quality": 95,
        },
    )
    assert resp.status_code == 200
    export_data = resp.json()
    assert export_data["export_format"] == "jpeg"
    assert export_data["quality"] == 95
    assert export_data["output_url"] is not None

    # Download exported file
    resp = await client.get(f"/api/grading/exports/{export_data['id']}/download")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_file_type(client):
    resp = await client.post("/api/style/sessions", json={})
    session_id = resp.json()["id"]

    resp = await client.post(
        f"/api/style/sessions/{session_id}/rounds",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_select_before_options(client):
    """Selecting from a non-existent round should fail."""
    resp = await client.post(
        "/api/style/rounds/nonexistent/select",
        json={"option_id": "fake"},
    )
    assert resp.status_code in (400, 404)


@pytest.mark.asyncio
async def test_analyze_without_enough_rounds(client):
    """Analyzing without any selections should return 400."""
    mock_ai = AsyncMock()

    with patch("app.api.style.get_current_provider", return_value=mock_ai):
        resp = await client.post("/api/style/sessions", json={})
        session_id = resp.json()["id"]

        # Analyze with no rounds — service raises ValueError → 400
        resp = await client.post(f"/api/style/sessions/{session_id}/analyze")
        assert resp.status_code == 400
        assert "No selections" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_export_task_not_found(client):
    resp = await client.post(
        "/api/grading/tasks/nonexistent/export",
        json={
            "parameters": ColorParams().model_dump(),
            "format": "jpeg",
            "quality": 95,
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_multiple_previews_same_task(client):
    """Generating multiple previews shouldn't fail."""
    resp = await client.post("/api/style/sessions", json={})
    user_id = resp.json()["user_id"]

    png_data = make_test_png()
    resp = await client.post(
        "/api/grading/tasks",
        data={"user_id": user_id},
        files={"file": ("test.png", png_data, "image/png")},
    )
    task_id = resp.json()["id"]

    # Generate 5 previews with different params
    for i in range(5):
        params = ColorParams(basic=BasicParams(exposure=i * 0.5 - 1.0))
        resp = await client.post(
            f"/api/grading/tasks/{task_id}/preview",
            json={"parameters": params.model_dump()},
        )
        assert resp.status_code == 200
