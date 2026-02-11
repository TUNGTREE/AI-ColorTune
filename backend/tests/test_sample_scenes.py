"""Tests for sample scenes API endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import Base, engine
from app.services.sample_scenes import get_sample_list, get_sample_image_path, SAMPLES


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def test_get_sample_list():
    """get_sample_list returns 12 samples with required fields."""
    samples = get_sample_list()
    assert len(samples) == 12
    for s in samples:
        assert "id" in s
        assert "scene_type" in s
        assert "time_of_day" in s
        assert "label_zh" in s
        assert "label_en" in s
        assert "thumbnail_url" in s
        assert s["thumbnail_url"].startswith("/samples/")


def test_get_sample_image_path_valid():
    """get_sample_image_path returns a valid path for known sample IDs."""
    path = get_sample_image_path("street_sunrise")
    assert path is not None
    assert path.exists()
    assert path.suffix == ".jpg"


def test_get_sample_image_path_invalid():
    """get_sample_image_path returns None for unknown sample ID."""
    path = get_sample_image_path("nonexistent_scene")
    assert path is None


def test_sample_image_is_valid_jpeg():
    """Generated sample images are valid JPEG files."""
    from PIL import Image
    path = get_sample_image_path("city_night")
    assert path is not None
    img = Image.open(path)
    assert img.size == (800, 533)
    assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_api_list_samples(client):
    """GET /api/style/samples returns 12 samples."""
    resp = await client.get("/api/style/samples")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 12
    # Check first sample has required fields
    sample = data[0]
    assert "id" in sample
    assert "thumbnail_url" in sample


def _mock_style_options():
    from app.core.color_params import ColorParams
    return [
        {"style_name": f"Style {i}", "parameters": ColorParams().model_dump()}
        for i in range(4)
    ]


@pytest.mark.asyncio
async def test_api_create_round_from_sample(client):
    """POST /api/style/sessions/{id}/rounds/sample creates a round with mocked AI."""
    # Create a session first
    resp = await client.post("/api/style/sessions", json={})
    assert resp.status_code == 200
    session_id = resp.json()["id"]

    mock_ai = AsyncMock()
    mock_ai.analyze_scene = AsyncMock(return_value={"scene_type": "ocean", "time_of_day": "sunset"})
    mock_ai.generate_style_options = AsyncMock(return_value=_mock_style_options())

    with patch("app.api.style.get_current_provider", return_value=mock_ai):
        resp = await client.post(
            f"/api/style/sessions/{session_id}/rounds/sample",
            json={"sample_id": "ocean_sunset"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["scene_type"] == "ocean"
    assert data["time_of_day"] == "sunset"
    assert data["original_image_url"] is not None
    assert len(data["options"]) == 4


@pytest.mark.asyncio
async def test_api_create_round_from_invalid_sample(client):
    """POST /api/style/sessions/{id}/rounds/sample returns 400 for invalid sample."""
    resp = await client.post("/api/style/sessions", json={})
    session_id = resp.json()["id"]

    resp = await client.post(
        f"/api/style/sessions/{session_id}/rounds/sample",
        json={"sample_id": "nonexistent"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_create_round_from_sample_invalid_session(client):
    """POST with invalid session_id returns 404."""
    resp = await client.post(
        "/api/style/sessions/nonexistent-session/rounds/sample",
        json={"sample_id": "ocean_sunset"},
    )
    assert resp.status_code == 404
