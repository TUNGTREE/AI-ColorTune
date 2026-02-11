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


@router.get("/providers")
def list_providers():
    """List available AI providers."""
    return {
        "providers": AIProviderFactory.available_providers(),
        "current": _current_provider,
    }


@router.put("/provider")
def set_provider(config: ProviderConfig):
    """Switch active AI provider."""
    global _current_provider, _current_model
    if config.provider not in AIProviderFactory.available_providers():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {config.provider}",
        )
    _current_provider = config.provider
    _current_model = config.model
    # API key is stored server-side only, never returned
    if config.api_key:
        if config.provider == "claude":
            settings.CLAUDE_API_KEY = config.api_key
        elif config.provider == "openai":
            settings.OPENAI_API_KEY = config.api_key
    if config.base_url:
        settings.OPENAI_BASE_URL = config.base_url
    return {"status": "ok", "provider": _current_provider}


def get_current_provider():
    """Get the currently configured AI provider instance."""
    api_key = (
        settings.CLAUDE_API_KEY if _current_provider == "claude"
        else settings.OPENAI_API_KEY
    )
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"API key not configured for provider: {_current_provider}",
        )
    base_url = settings.OPENAI_BASE_URL if _current_provider == "openai" else None
    return AIProviderFactory.get_provider(_current_provider, api_key, _current_model, base_url)
