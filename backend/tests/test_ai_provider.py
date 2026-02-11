"""Tests for AI provider abstraction layer (Phase 2).

All tests use mocks - no real API calls.
"""
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.color_params import ColorParams
from app.services.ai_provider import (
    AIProviderFactory,
    ClaudeProvider,
    OpenAIProvider,
    _extract_json,
)
from app.main import app


# ---------------------------------------------------------------------------
# Helper: valid AI response fixtures
# ---------------------------------------------------------------------------

MOCK_SCENE_RESPONSE = json.dumps({
    "scene_type": "landscape",
    "time_of_day": "golden_hour",
    "weather": "sunny",
    "dominant_colors": ["orange", "blue", "green"],
    "color_temperature_feel": "warm",
    "mood": "serene",
    "subjects": ["mountains", "lake"],
    "composition": "rule of thirds",
})

MOCK_STYLE_OPTIONS_RESPONSE = json.dumps([
    {
        "style_name": "Cinematic Teal & Orange",
        "description": "Classic cinema look",
        "parameters": ColorParams(
            basic={"exposure": 0.3, "contrast": 25, "highlights": -20,
                   "shadows": 15, "whites": 10, "blacks": -10},
            color={"temperature": 7500, "tint": 5, "vibrance": 20, "saturation": 10},
            effects={"clarity": 15, "dehaze": 0, "vignette": -20, "grain": 5},
        ).model_dump(),
    },
    {
        "style_name": "Clean & Bright",
        "description": "Bright airy look",
        "parameters": ColorParams(
            basic={"exposure": 0.5, "contrast": -10, "highlights": -30,
                   "shadows": 40, "whites": 20, "blacks": 10},
            color={"temperature": 6800, "tint": 0, "vibrance": 15, "saturation": -5},
            effects={"clarity": 10, "dehaze": 5, "vignette": 0, "grain": 0},
        ).model_dump(),
    },
])

MOCK_PREFERENCE_RESPONSE = json.dumps({
    "temperature_preference": "warm",
    "contrast_preference": "medium",
    "saturation_preference": "moderate",
    "tone_preference": "balanced",
    "color_tendencies": ["warm tones", "orange highlights"],
    "effects_notes": "Prefers subtle clarity with light vignette",
    "overall_style_summary": "User prefers warm, balanced looks with moderate contrast.",
    "reference_styles": ["Film Emulation", "Golden Hour"],
})

MOCK_SUGGESTION_RESPONSE = json.dumps([
    {
        "suggestion_name": "Warm Golden",
        "description": "Matches warm preference",
        "parameters": ColorParams(
            basic={"exposure": 0.2, "contrast": 15, "highlights": -10,
                   "shadows": 20, "whites": 5, "blacks": -5},
            color={"temperature": 7200, "tint": 3, "vibrance": 15, "saturation": 5},
        ).model_dump(),
    },
])


# ---------------------------------------------------------------------------
# _extract_json helper tests
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_plain_json(self):
        result = _extract_json('{"key": "value"}')
        assert json.loads(result) == {"key": "value"}

    def test_markdown_fenced(self):
        result = _extract_json('```json\n{"key": "value"}\n```')
        assert json.loads(result) == {"key": "value"}

    def test_with_preamble(self):
        result = _extract_json('Here is the result:\n[{"a": 1}]')
        assert json.loads(result) == [{"a": 1}]

    def test_array(self):
        result = _extract_json('[1, 2, 3]')
        assert json.loads(result) == [1, 2, 3]


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

class TestAIProviderFactory:
    def test_available_providers(self):
        providers = AIProviderFactory.available_providers()
        assert "claude" in providers
        assert "openai" in providers

    def test_get_claude_provider(self):
        provider = AIProviderFactory.get_provider("claude", "test-key")
        assert isinstance(provider, ClaudeProvider)
        assert provider.provider_name == "claude"

    def test_get_openai_provider(self):
        provider = AIProviderFactory.get_provider("openai", "test-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_name == "openai"

    def test_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            AIProviderFactory.get_provider("unknown", "key")

    def test_switch_providers(self):
        p1 = AIProviderFactory.get_provider("claude", "key1")
        p2 = AIProviderFactory.get_provider("openai", "key2")
        assert p1.provider_name != p2.provider_name


# ---------------------------------------------------------------------------
# Claude provider mock tests
# ---------------------------------------------------------------------------

class TestClaudeProvider:
    @pytest.mark.asyncio
    async def test_analyze_scene(self):
        provider = ClaudeProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=MOCK_SCENE_RESPONSE)]

        with patch.object(provider._client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.analyze_scene("fake_base64_data")
            assert result["scene_type"] == "landscape"
            assert result["time_of_day"] == "golden_hour"

    @pytest.mark.asyncio
    async def test_generate_style_options(self):
        provider = ClaudeProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=MOCK_STYLE_OPTIONS_RESPONSE)]

        with patch.object(provider._client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.generate_style_options("fake", {"scene_type": "landscape"})
            assert len(result) == 2
            assert "parameters" in result[0]
            # Verify parameters can be parsed as ColorParams
            params = ColorParams(**result[0]["parameters"])
            assert params.basic.exposure == 0.3

    @pytest.mark.asyncio
    async def test_generate_grading_suggestions(self):
        provider = ClaudeProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=MOCK_SUGGESTION_RESPONSE)]

        with patch.object(provider._client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.generate_grading_suggestions("fake", {"style": "warm"})
            assert len(result) == 1
            params = ColorParams(**result[0]["parameters"])
            assert params.color.temperature == 7200


# ---------------------------------------------------------------------------
# OpenAI provider mock tests
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    @pytest.mark.asyncio
    async def test_analyze_scene(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=MOCK_SCENE_RESPONSE))]

        with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.analyze_scene("fake_base64_data")
            assert result["scene_type"] == "landscape"

    @pytest.mark.asyncio
    async def test_generate_style_options(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=MOCK_STYLE_OPTIONS_RESPONSE))]

        with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.generate_style_options("fake", {"scene_type": "test"})
            assert len(result) == 2
            params = ColorParams(**result[0]["parameters"])
            assert params.basic.contrast == 25


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        provider = ClaudeProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is not JSON at all")]

        with patch.object(provider._client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(json.JSONDecodeError):
                await provider.analyze_scene("fake")

    @pytest.mark.asyncio
    async def test_partial_json_response(self):
        """AI returns JSON but with extra text around it."""
        provider = ClaudeProvider(api_key="test-key")
        wrapped = f"Here is the analysis:\n```json\n{MOCK_SCENE_RESPONSE}\n```\nHope this helps!"
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=wrapped)]

        with patch.object(provider._client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.analyze_scene("fake")
            assert result["scene_type"] == "landscape"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_list_providers(client):
    resp = await client.get("/api/ai/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "claude" in data["providers"]
    assert "openai" in data["providers"]


@pytest.mark.asyncio
async def test_set_provider(client):
    resp = await client.put(
        "/api/ai/provider",
        json={"provider": "openai", "api_key": "sk-test"},
    )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "openai"


@pytest.mark.asyncio
async def test_set_invalid_provider(client):
    resp = await client.put(
        "/api/ai/provider",
        json={"provider": "invalid_provider"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_key_not_in_response(client):
    """API key should never appear in responses."""
    resp = await client.put(
        "/api/ai/provider",
        json={"provider": "claude", "api_key": "sk-secret-key-12345"},
    )
    assert resp.status_code == 200
    response_text = resp.text
    assert "sk-secret-key-12345" not in response_text

    # Also check list endpoint
    resp2 = await client.get("/api/ai/providers")
    assert "sk-secret-key-12345" not in resp2.text
