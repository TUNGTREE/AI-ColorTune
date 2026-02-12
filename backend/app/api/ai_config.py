"""AI provider configuration API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.ai_provider import AIProviderFactory

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ProviderConfig(BaseModel):
    provider: str
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None  # Custom base URL for OpenAI-compatible APIs


# In-memory session state (per-process; for production use Redis or DB)
_current_provider: str = settings.DEFAULT_AI_PROVIDER
_current_model: str | None = settings.DEFAULT_AI_MODEL or None
_current_base_url: str | None = getattr(settings, "OPENAI_BASE_URL", None)

# Per-provider API key storage (populated from settings on startup)
_api_keys: dict[str, str] = {}


def _init_keys():
    """Initialize API keys from settings."""
    if settings.CLAUDE_API_KEY:
        _api_keys["claude"] = settings.CLAUDE_API_KEY
    if settings.OPENAI_API_KEY:
        _api_keys["openai"] = settings.OPENAI_API_KEY
    if settings.DEEPSEEK_API_KEY:
        _api_keys["deepseek"] = settings.DEEPSEEK_API_KEY
    if settings.GLM_API_KEY:
        _api_keys["glm"] = settings.GLM_API_KEY


_init_keys()


def _get_api_key(provider: str) -> str:
    """Get API key for a given provider."""
    return _api_keys.get(provider, "")


def _mask_key(key: str | None) -> str:
    """Return a masked version of an API key for display."""
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


# Provider display names
_PROVIDER_LABELS: dict[str, str] = {
    "claude": "Claude (Anthropic)",
    "openai": "OpenAI / Compatible",
    "deepseek": "DeepSeek",
    "glm": "GLM (ZhipuAI)",
}

# Default models per provider
_DEFAULT_MODELS: dict[str, str] = {
    "claude": "claude-sonnet-4-5-20250929",
    "openai": "gpt-4o",
    "deepseek": "deepseek-chat",
    "glm": "glm-4v-flash",
}


@router.get("/providers")
def list_providers():
    """List available AI providers and current configuration."""
    api_key = _get_api_key(_current_provider)
    return {
        "providers": AIProviderFactory.available_providers(),
        "provider_labels": _PROVIDER_LABELS,
        "default_models": _DEFAULT_MODELS,
        "current": _current_provider,
        "model": _current_model or "",
        "base_url": _current_base_url or "",
        "api_key_masked": _mask_key(api_key),
        "api_key_set": bool(api_key),
    }


@router.put("/provider")
def set_provider(config: ProviderConfig):
    """Switch active AI provider."""
    global _current_provider, _current_model, _current_base_url
    if config.provider not in AIProviderFactory.available_providers():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {config.provider}",
        )
    _current_provider = config.provider
    _current_model = config.model
    # Store API key per provider
    if config.api_key:
        _api_keys[config.provider] = config.api_key
        # Also update settings for backward compat
        if config.provider == "claude":
            settings.CLAUDE_API_KEY = config.api_key
        elif config.provider == "openai":
            settings.OPENAI_API_KEY = config.api_key
        elif config.provider == "deepseek":
            settings.DEEPSEEK_API_KEY = config.api_key
        elif config.provider == "glm":
            settings.GLM_API_KEY = config.api_key
    if config.base_url is not None:
        _current_base_url = config.base_url
    return {"status": "ok", "provider": _current_provider}


def get_current_provider():
    """Get the currently configured AI provider instance."""
    api_key = _get_api_key(_current_provider)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"API key not configured for provider: {_current_provider}",
        )
    base_url = _current_base_url if _current_provider in ("openai", "deepseek", "glm") else None
    return AIProviderFactory.get_provider(_current_provider, api_key, _current_model, base_url)
