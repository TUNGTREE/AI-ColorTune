"""Multi-model AI provider abstraction layer."""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

import anthropic
import openai

from app.core.prompts import (
    SCENE_ANALYSIS_PROMPT,
    STYLE_OPTIONS_PROMPT,
    PREFERENCE_ANALYSIS_PROMPT,
    GRADING_SUGGESTION_PROMPT,
    COLOR_PARAMS_SCHEMA_DESCRIPTION,
)

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    """Extract JSON from AI response that may contain markdown fences or preamble."""
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Try direct parse first
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Find all possible JSON substrings and return the longest valid one
    candidates = []
    for start_char, end_char in [('[', ']'), ('{', '}')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                json.loads(candidate)
                candidates.append(candidate)
            except json.JSONDecodeError:
                pass

    if candidates:
        return max(candidates, key=len)
    return text


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def analyze_image(self, image_base64: str, prompt: str) -> str:
        """Send an image + text prompt, return text response."""
        ...

    async def analyze_scene(self, image_base64: str) -> dict:
        """Analyze scene of a photograph."""
        response = await self.analyze_image(image_base64, SCENE_ANALYSIS_PROMPT)
        return json.loads(_extract_json(response))

    async def generate_style_options(
        self, image_base64: str, scene_info: dict, num_styles: int = 4
    ) -> list[dict]:
        """Generate multiple style options for a photo."""
        prompt = STYLE_OPTIONS_PROMPT.format(
            num_styles=num_styles,
            scene_info=json.dumps(scene_info, indent=2),
            schema=COLOR_PARAMS_SCHEMA_DESCRIPTION,
        )
        response = await self.analyze_image(image_base64, prompt)
        return json.loads(_extract_json(response))

    async def analyze_preferences(self, selections: list[dict]) -> dict:
        """Analyze user's style preferences from their selections."""
        prompt = PREFERENCE_ANALYSIS_PROMPT.format(
            selections=json.dumps(selections, indent=2),
            num_rounds=len(selections),
        )
        # This is text-only, no image needed — use a simple text call
        response = await self.analyze_image("", prompt)
        return json.loads(_extract_json(response))

    async def generate_grading_suggestions(
        self, image_base64: str, user_profile: dict, num_suggestions: int = 3
    ) -> list[dict]:
        """Generate personalized grading suggestions."""
        prompt = GRADING_SUGGESTION_PROMPT.format(
            num_suggestions=num_suggestions,
            user_profile=json.dumps(user_profile, indent=2),
            schema=COLOR_PARAMS_SCHEMA_DESCRIPTION,
        )
        response = await self.analyze_image(image_base64, prompt)
        return json.loads(_extract_json(response))


class ClaudeProvider(AIProvider):
    """Claude (Anthropic) AI provider."""

    def __init__(self, api_key: str, model: str | None = None):
        super().__init__(api_key, model or "claude-sonnet-4-5-20250929")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "claude"

    async def analyze_image(self, image_base64: str, prompt: str) -> str:
        content = []
        if image_base64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64,
                },
            })
        content.append({"type": "text", "text": prompt})

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text


class OpenAIProvider(AIProvider):
    """OpenAI-compatible AI provider (also supports DashScope/Qwen, etc.)."""

    def __init__(self, api_key: str, model: str | None = None, base_url: str | None = None):
        super().__init__(api_key, model or "gpt-4o")
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.AsyncOpenAI(**kwargs)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def analyze_image(self, image_base64: str, prompt: str) -> str:
        content = []
        if image_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
            })
        content.append({"type": "text", "text": prompt})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096,
        )
        return response.choices[0].message.content


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek AI provider (OpenAI-compatible API)."""

    def __init__(self, api_key: str, model: str | None = None, base_url: str | None = None):
        super().__init__(
            api_key=api_key,
            model=model or "deepseek-chat",
            base_url=base_url or "https://api.deepseek.com",
        )

    @property
    def provider_name(self) -> str:
        return "deepseek"


class GLMProvider(OpenAIProvider):
    """GLM / ZhipuAI provider (OpenAI-compatible API)."""

    def __init__(self, api_key: str, model: str | None = None, base_url: str | None = None):
        super().__init__(
            api_key=api_key,
            model=model or "glm-4v-flash",
            base_url=base_url or "https://open.bigmodel.cn/api/paas/v4",
        )

    @property
    def provider_name(self) -> str:
        return "glm"


class AIProviderFactory:
    """Factory for creating AI provider instances."""

    _providers: dict[str, type[AIProvider]] = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "deepseek": DeepSeekProvider,
        "glm": GLMProvider,
    }

    @classmethod
    def get_provider(cls, name: str, api_key: str, model: str | None = None, base_url: str | None = None) -> AIProvider:
        provider_cls = cls._providers.get(name)
        if provider_cls is None:
            raise ValueError(f"Unknown provider: {name}. Available: {list(cls._providers.keys())}")
        if name in ("openai", "deepseek", "glm"):
            return provider_cls(api_key=api_key, model=model, base_url=base_url)
        return provider_cls(api_key=api_key, model=model)

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def register_provider(cls, name: str, provider_cls: type[AIProvider]):
        cls._providers[name] = provider_cls
