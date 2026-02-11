import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import Base, engine


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "ColorTune"


@pytest.mark.asyncio
async def test_upload_invalid_extension(client):
    resp = await client.post(
        "/api/upload",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_valid_image(client):
    # Create a minimal valid PNG (1x1 pixel)
    import struct
    import zlib

    def make_png():
        sig = b"\x89PNG\r\n\x1a\n"

        def chunk(ctype, data):
            c = ctype + data
            crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return struct.pack(">I", len(data)) + c + crc

        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        raw = zlib.compress(b"\x00\xff\x00\x00")
        return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")

    png_data = make_png()
    resp = await client.post(
        "/api/upload",
        files={"file": ("test.png", png_data, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["filename"].endswith(".png")


def test_database_tables():
    """Verify all tables are created."""
    from app.models.user import User
    from app.models.style import StyleSession, StyleRound, StyleOption, UserStyleProfile
    from app.models.grading import GradingTask, GradingSuggestion, Export

    Base.metadata.create_all(bind=engine)
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "users", "style_sessions", "style_rounds", "style_options",
        "user_style_profiles", "grading_tasks", "grading_suggestions", "exports",
    }
    assert expected.issubset(table_names), f"Missing tables: {expected - table_names}"
