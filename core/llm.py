from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol

import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    usage: Dict[str, Any]


class LLMClient(Protocol):
    """Minimal client interface for generative models."""

    async def generate(self, messages: Iterable[LLMMessage], **kwargs: Any) -> LLMResponse:
        ...


class OpenAIClient:
    """Wrapper over the official OpenAI client."""

    def __init__(self, model: str, api_key: Optional[str] = None, timeout: float = 30.0):
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required for OpenAIClient. Please install openai>=1.0."
            ) from exc

        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.timeout = timeout

    async def generate(
        self,
        messages: Iterable[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        messages_payload = [{"role": m.role, "content": m.content} for m in messages]
        response = await self._client.chat.completions.create(
            model=self.model, messages=messages_payload, timeout=self.timeout, **kwargs
        )
        choice = response.choices[0]
        content = choice.message.content or ""
        usage = response.usage.model_dump() if hasattr(response.usage, "model_dump") else {}
        return LLMResponse(content=content, usage=usage)


class OpenRouterClient:
    """HTTP client for OpenRouter chat completions."""

    def __init__(
        self,
        model: str,
        api_key: str,
        endpoint: str = "https://openrouter.ai/api/v1/chat/completions",
        timeout: float = 40.0,
    ):
        if not api_key:
            raise ValueError("OpenRouter API key is required.")
        self.model = model
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout = timeout

    async def generate(
        self,
        messages: Iterable[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        payload.update(kwargs)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://mini-perplexity.local",
            "X-Title": "Mini-Perplexity ACE",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return LLMResponse(content=content, usage=usage)


class EchoClient:
    """Fallback LLM client for offline development."""

    def __init__(self, tag: str = "echo"):
        self.tag = tag

    async def generate(
        self,
        messages: Iterable[LLMMessage],
        **_: Any,
    ) -> LLMResponse:
        collected = "\n\n".join(f"[{m.role}] {m.content}" for m in messages)
        logger.warning("EchoClient returning request payload because no LLM is configured.")
        return LLMResponse(
            content=f"[{self.tag} mock response]\n{collected}",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )


class LLMClientFactory:
    """Factory that builds LLM clients from configuration dictionaries."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def build(self, section: str) -> LLMClient:
        section_cfg = self.config.get(section) or {}
        provider = section_cfg.get("provider", "echo")
        if provider == "openai":
            model = section_cfg.get("model")
            if not model:
                raise ValueError(f"Missing model for {section} LLM configuration.")
            api_key = section_cfg.get("api_key")
            return OpenAIClient(model=model, api_key=api_key)
        if provider == "openrouter":
            model = section_cfg.get("model")
            api_key = section_cfg.get("api_key")
            endpoint = section_cfg.get("endpoint", "https://openrouter.ai/api/v1/chat/completions")
            if not model or not api_key:
                raise ValueError(f"OpenRouter configuration requires model and api_key for {section}.")
            return OpenRouterClient(model=model, api_key=api_key, endpoint=endpoint)
        if provider == "echo":
            return EchoClient(tag=section)
        raise ValueError(f"Unsupported LLM provider: {provider}")
