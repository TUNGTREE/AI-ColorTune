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


def _repair_truncated_json(text: str) -> str:
    """Attempt to repair truncated JSON arrays by keeping only complete objects.

    When max_tokens is hit, the model output is cut mid-JSON. This function
    finds the last complete top-level object in an array and closes the array.
    """
    text = text.strip()
    if not text.startswith("["):
        return text

    # Find positions of all top-level complete objects by tracking brace depth
    depth = 0
    in_string = False
    escape_next = False
    last_complete_end = -1

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            if in_string:
                escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_complete_end = i

    if last_complete_end > 0:
        repaired = text[:last_complete_end + 1].rstrip().rstrip(",") + "\n]"
        try:
            json.loads(repaired)
            logger.warning(
                "Repaired truncated JSON array (kept up to char %d of %d)",
                last_complete_end + 1, len(text),
            )
            return repaired
        except json.JSONDecodeError:
            pass
    return text


def _extract_json(text: str | None) -> str:
    """Extract JSON from AI response that may contain markdown fences or preamble."""
    if not text:
        return ""
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

    # Last resort: try to repair truncated JSON (e.g. from max_tokens cutoff)
    repaired = _repair_truncated_json(text)
    if repaired != text:
        return repaired

    return text


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    _max_tokens: int = 8192

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
        return self._parse_json_response(response, "scene analysis")

    async def generate_style_options(
        self, image_base64: str, scene_info: dict, num_styles: int = 6,
        custom_prompt: str | None = None,
        avoid_styles: list[str] | None = None,
    ) -> list[dict]:
        """Generate multiple style options for a photo."""
        if custom_prompt:
            prompt = custom_prompt
        else:
            # Build the avoid section
            if avoid_styles:
                avoid_section = (
                    "## AVOID PREVIOUSLY GENERATED STYLES\n"
                    "The following styles were already generated and the user wants NEW options. "
                    "You MUST choose DIFFERENT archetypes and axis positions. "
                    "Do NOT reuse any of these styles or produce visually similar results:\n"
                    + "\n".join(f"- {name}" for name in avoid_styles)
                    + "\n\nPick from the remaining archetypes in the library that were NOT used above."
                )
            else:
                avoid_section = ""
            prompt = STYLE_OPTIONS_PROMPT.format(
                num_styles=num_styles,
                scene_info=json.dumps(scene_info, indent=2),
                schema=COLOR_PARAMS_SCHEMA_DESCRIPTION,
                avoid_section=avoid_section,
            )
        response = await self.analyze_image(image_base64, prompt)
        return self._parse_json_response(response, "style options")

    async def analyze_preferences(self, selections: list[dict]) -> dict:
        """Analyze user's style preferences from their selections."""
        prompt = PREFERENCE_ANALYSIS_PROMPT.format(
            selections=json.dumps(selections, indent=2),
            num_rounds=len(selections),
        )
        # This is text-only, no image needed — use a simple text call
        response = await self.analyze_image("", prompt)
        return self._parse_json_response(response, "preference analysis")

    async def generate_grading_suggestions(
        self, image_base64: str, user_profile: dict, num_suggestions: int = 3,
        custom_prompt: str | None = None
    ) -> list[dict]:
        """Generate personalized grading suggestions."""
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = GRADING_SUGGESTION_PROMPT.format(
                num_suggestions=num_suggestions,
                user_profile=json.dumps(user_profile, indent=2),
                schema=COLOR_PARAMS_SCHEMA_DESCRIPTION,
            )
        response = await self.analyze_image(image_base64, prompt)
        return self._parse_json_response(response, "grading suggestions")

    def _parse_json_response(self, response: str, context: str):
        """Parse JSON from AI response with clear error reporting."""
        if not response:
            raise ValueError(
                f"AI returned empty response for {context}. "
                "The model may not support this request or content was filtered."
            )
        extracted = _extract_json(response)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError as e:
            preview = response[:300]
            logger.error(
                "Failed to parse %s JSON. Error: %s\nRaw response (first 300 chars): %s",
                context, e, preview,
            )
            raise ValueError(
                f"AI response for {context} is not valid JSON. "
                f"Raw response preview: {preview}"
            ) from e


class ClaudeProvider(AIProvider):
    """Claude (Anthropic) AI provider."""

    _max_tokens = 16384

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
            max_tokens=self._max_tokens,
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
            max_tokens=self._max_tokens,
        )
        result = response.choices[0].message.content
        logger.debug("AI raw response from %s (first 500 chars): %.500s", self.model, result)
        return result or ""


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
