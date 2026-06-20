"""LLM Provider Service - unified abstraction over multiple LLM vendors.

Implements the llm-provider spec:
- A single interface that extraction and other capabilities depend on,
  so switching provider requires no change to upper-layer code.
- API key, model name and proxy are read from configuration (env-backed).
- The API key MUST NOT be echoed, returned, or written to any log/store.
- Outbound calls go through the configured proxy.
- Token usage of every call is recorded for cost observability.

The default provider is DeepSeek (deepseek-v4-pro).
"""

from __future__ import annotations

import json
import logging
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("first_story.llm")


class LLMNotConfiguredError(RuntimeError):
    """Raised when an LLM call is attempted without a configured API key."""


@dataclass
class TokenUsage:
    """Token usage for a single LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Result of an LLM completion call.

    Note: never place the API key in this structure.
    """

    text: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)


@dataclass
class TokenUsageTracker:
    """Accumulates token usage across calls for cost observability."""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def record(self, usage: TokenUsage) -> None:
        self.calls += 1
        self.prompt_tokens += usage.prompt_tokens
        self.completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        # Log usage only - never the key or full content.
        logger.info(
            "llm call recorded: prompt=%d completion=%d total=%d (cumulative total=%d)",
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
            self.total_tokens,
        )

    def snapshot(self) -> dict[str, int]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


def _redact(text: str, api_key: str) -> str:
    """Remove the API key from any text before it could be logged/returned."""
    if api_key and api_key in text:
        return text.replace(api_key, "***REDACTED***")
    return text


class LLMProvider(ABC):
    """Abstract LLM interface. Upper layers depend on this, not a vendor SDK."""

    def __init__(self, tracker: Optional[TokenUsageTracker] = None) -> None:
        self.tracker = tracker or TokenUsageTracker()

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'deepseek')."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Default model name in use."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Run a single completion. Implementations MUST record token usage."""


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider using the OpenAI-compatible chat completions API.

    Uses only the stdlib so no vendor SDK is bound. Outbound requests go
    through the configured proxy.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "deepseek-v4-pro",
        base_url: str = "https://api.deepseek.com",
        proxy: str = "",
        timeout: float = 60.0,
        tracker: Optional[TokenUsageTracker] = None,
    ) -> None:
        super().__init__(tracker)
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._proxy = proxy
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def model(self) -> str:
        return self._model

    def _build_opener(self) -> urllib.request.OpenerDirector:
        if self._proxy:
            handler = urllib.request.ProxyHandler(
                {"http": self._proxy, "https": self._proxy}
            )
            return urllib.request.build_opener(handler)
        # Explicitly no proxy.
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self._api_key:
            raise LLMNotConfiguredError(
                "LLM API key is not configured. Set FIRST_STORY_LLM_API_KEY "
                "in your environment or .env file."
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=data,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self._api_key}")

        opener = self._build_opener()
        try:
            with opener.open(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001 - redact before re-raising
            safe = _redact(str(exc), self._api_key)
            raise RuntimeError(f"LLM request failed: {safe}") from None

        payload = json.loads(raw)
        choice = payload.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")

        usage_data = payload.get("usage", {}) or {}
        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )
        self.tracker.record(usage)

        return LLMResponse(text=text, model=self._model, usage=usage)


# Registry of available providers for pluggability.
_PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "deepseek": DeepSeekProvider,
}


def build_provider(
    *,
    provider: str,
    api_key: str,
    model: str,
    base_url: str,
    proxy: str,
    timeout: float = 60.0,
    tracker: Optional[TokenUsageTracker] = None,
) -> LLMProvider:
    """Construct a provider by name.

    The provider name selects the implementation; upper layers never need to
    change when the provider is swapped via configuration.
    """
    key = provider.lower()
    impl = _PROVIDER_REGISTRY.get(key)
    if impl is None:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            f"Available: {', '.join(sorted(_PROVIDER_REGISTRY))}"
        )
    # All current providers share the DeepSeek-style constructor signature.
    return impl(
        api_key=api_key,
        model=model,
        base_url=base_url,
        proxy=proxy,
        timeout=timeout,
        tracker=tracker,
    )


def get_provider(settings=None, tracker: Optional[TokenUsageTracker] = None) -> LLMProvider:
    """Build the configured provider from application settings."""
    if settings is None:
        from ..config import get_settings

        settings = get_settings()
    return build_provider(
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        proxy=settings.llm_proxy,
        timeout=settings.llm_timeout_seconds,
        tracker=tracker,
    )
