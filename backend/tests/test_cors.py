"""Test CORS connectivity - verifies frontend origin is allowed."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_cors_preflight(client):
    """Simulate browser CORS preflight from frontend origin."""
    resp = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert resp.status_code == 200
    assert "http://localhost:5173" in resp.headers.get("access-control-allow-origin", "")


@pytest.mark.asyncio
async def test_cors_actual_request(client):
    """Simulate actual GET with Origin header."""
    resp = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
