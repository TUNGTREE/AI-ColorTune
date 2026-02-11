"""Tests for Export (Phase 6).

Tests export in JPEG/PNG/TIFF, quality settings, and download endpoint.
"""
import struct
import uuid
import zlib

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import Base, engine, SessionLocal
from app.core.color_params import ColorParams, BasicParams, ColorAdjustParams
from app.services.grading_service import GradingService
from app.models.user import User


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


# ---------------------------------------------------------------------------
# Service-level export tests
# ---------------------------------------------------------------------------

class TestExportService:
    def test_export_jpeg(self, db):
        user = User(id="user-exp-1")
        db.add(user)
        db.commit()

        from app.config import settings
        import numpy as np
        from PIL import Image
        img_path = settings.UPLOAD_DIR / "test_export.png"
        Image.fromarray(np.full((100, 100, 3), 128, dtype=np.uint8)).save(img_path)

        svc = GradingService(db)
        task = svc.create_task("user-exp-1", str(img_path))
        params = ColorParams(basic=BasicParams(exposure=0.3, contrast=20))
        export = svc.export_image(task, params, fmt="jpeg", quality=90)
        assert export.export_format == "jpeg"
        assert export.quality == 90
        assert export.output_image_path.endswith(".jpg")
        assert task.status == "exported"

    def test_export_png(self, db):
        user = User(id="user-exp-2")
        db.add(user)
        db.commit()

        from app.config import settings
        import numpy as np
        from PIL import Image
        img_path = settings.UPLOAD_DIR / "test_export_png.png"
        Image.fromarray(np.full((50, 50, 3), 100, dtype=np.uint8)).save(img_path)

        svc = GradingService(db)
        task = svc.create_task("user-exp-2", str(img_path))
        params = ColorParams()
        export = svc.export_image(task, params, fmt="png")
        assert export.export_format == "png"
        assert export.output_image_path.endswith(".png")

    def test_export_tiff(self, db):
        user = User(id="user-exp-3")
        db.add(user)
        db.commit()

        from app.config import settings
        import numpy as np
        from PIL import Image
        img_path = settings.UPLOAD_DIR / "test_export_tiff.png"
        Image.fromarray(np.full((50, 50, 3), 150, dtype=np.uint8)).save(img_path)

        svc = GradingService(db)
        task = svc.create_task("user-exp-3", str(img_path))
        params = ColorParams(color=ColorAdjustParams(temperature=8000))
        export = svc.export_image(task, params, fmt="tiff")
        assert export.export_format == "tiff"
        assert export.output_image_path.endswith(".tif")


# ---------------------------------------------------------------------------
# API-level export tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_api_jpeg(client):
    # Create user
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

    # Export JPEG
    params = ColorParams(basic=BasicParams(exposure=0.5, contrast=30))
    resp = await client.post(
        f"/api/grading/tasks/{task_id}/export",
        json={
            "parameters": params.model_dump(),
            "format": "jpeg",
            "quality": 85,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["export_format"] == "jpeg"
    assert data["quality"] == 85
    assert data["output_url"] is not None
    export_id = data["id"]

    # Download
    resp = await client.get(f"/api/grading/exports/{export_id}/download")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_export_api_png(client):
    resp = await client.post("/api/style/sessions", json={})
    user_id = resp.json()["user_id"]

    png_data = make_test_png()
    resp = await client.post(
        "/api/grading/tasks",
        data={"user_id": user_id},
        files={"file": ("test.png", png_data, "image/png")},
    )
    task_id = resp.json()["id"]

    params = ColorParams()
    resp = await client.post(
        f"/api/grading/tasks/{task_id}/export",
        json={"parameters": params.model_dump(), "format": "png"},
    )
    assert resp.status_code == 200
    assert resp.json()["export_format"] == "png"


@pytest.mark.asyncio
async def test_export_not_found(client):
    resp = await client.get("/api/grading/exports/nonexistent/download")
    assert resp.status_code == 404
