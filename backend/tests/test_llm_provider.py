"""Tests for the LLM provider abstraction (llm-provider spec).

These tests use a fake provider / monkeypatched transport - no real LLM call.
They verify:
- The abstraction is pluggable (swap provider without changing callers).
- The API key never leaks into logs, responses, or tracked usage.
- Missing key raises a clear error instead of crashing opaquely.
- Outbound calls go through the configured proxy.
- Token usage is recorded per call.
"""

import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.llm_provider import (  # noqa: E402
    DeepSeekProvider,
    LLMNotConfiguredError,
    LLMProvider,
    LLMResponse,
    TokenUsage,
    TokenUsageTracker,
    build_provider,
    get_provider,
)

SECRET_KEY = "sk-supersecret-test-0123456789"


class FakeProvider(LLMProvider):
    """A drop-in provider used to prove the abstraction is pluggable."""

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-model-1"

    def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=None):
        usage = TokenUsage(prompt_tokens=3, completion_tokens=5, total_tokens=8)
        self.tracker.record(usage)
        return LLMResponse(text=f"echo:{prompt}", model=self.model, usage=usage)


def _make_deepseek(monkeypatch, *, key=SECRET_KEY, response=None, proxy="http://127.0.0.1:7890"):
    """Build a DeepSeekProvider whose HTTP transport is faked."""
    provider = DeepSeekProvider(
        api_key=key,
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        proxy=proxy,
    )

    captured = {}

    class FakeResp:
        def __init__(self, payload):
            self._payload = json.dumps(payload).encode("utf-8")

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeOpener:
        def open(self, req, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = dict(req.header_items())
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp(
                response
                or {
                    "choices": [{"message": {"content": "结构化结果"}}],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 7,
                        "total_tokens": 19,
                    },
                }
            )

    monkeypatch.setattr(provider, "_build_opener", lambda: FakeOpener())
    return provider, captured


def test_abstraction_is_pluggable():
    """Callers depend on the LLMProvider interface, not a concrete vendor."""
    provider: LLMProvider = FakeProvider()
    result = provider.complete("hello")
    assert isinstance(result, LLMResponse)
    assert result.text == "echo:hello"
    # Swapping to another implementation keeps the same call shape.
    assert provider.tracker.total_tokens == 8


def test_build_provider_returns_deepseek_by_default():
    provider = build_provider(
        provider="deepseek",
        api_key=SECRET_KEY,
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        proxy="",
    )
    assert provider.name == "deepseek"
    assert provider.model == "deepseek-v4-pro"


def test_build_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_provider(
            provider="nope",
            api_key="x",
            model="m",
            base_url="u",
            proxy="",
        )


def test_missing_key_raises_clear_error():
    provider = DeepSeekProvider(api_key="", model="deepseek-v4-pro")
    with pytest.raises(LLMNotConfiguredError, match="not configured"):
        provider.complete("hi")


def test_successful_call_records_usage(monkeypatch):
    provider, _ = _make_deepseek(monkeypatch)
    result = provider.complete("提取这段", system="你是提取器")
    assert result.text == "结构化结果"
    assert result.usage.total_tokens == 19
    assert provider.tracker.calls == 1
    assert provider.tracker.total_tokens == 19


def test_request_uses_configured_proxy_and_auth(monkeypatch):
    provider, captured = _make_deepseek(monkeypatch)
    provider.complete("x")
    # Authorization header carries the bearer key for the request itself...
    assert captured["headers"].get("Authorization") == f"Bearer {SECRET_KEY}"
    assert "chat/completions" in captured["url"]


def test_key_never_leaks_into_logs(monkeypatch, caplog):
    provider, _ = _make_deepseek(monkeypatch)
    with caplog.at_level(logging.DEBUG, logger="first_story.llm"):
        provider.complete("x")
    for record in caplog.records:
        assert SECRET_KEY not in record.getMessage()


def test_key_never_leaks_into_response(monkeypatch):
    provider, _ = _make_deepseek(monkeypatch)
    result = provider.complete("x")
    # The response object and its repr must not carry the secret.
    assert SECRET_KEY not in repr(result)
    assert SECRET_KEY not in result.text


def test_key_redacted_on_transport_error(monkeypatch):
    """If the transport raises with the key in the message, it is redacted."""
    provider = DeepSeekProvider(api_key=SECRET_KEY, model="deepseek-v4-pro", proxy="")

    class BoomOpener:
        def open(self, req, timeout=None):
            raise RuntimeError(f"connection failed using key {SECRET_KEY}")

    monkeypatch.setattr(provider, "_build_opener", lambda: BoomOpener())
    with pytest.raises(RuntimeError) as excinfo:
        provider.complete("x")
    assert SECRET_KEY not in str(excinfo.value)
    assert "REDACTED" in str(excinfo.value)


def test_tracker_snapshot_has_no_key():
    tracker = TokenUsageTracker()
    tracker.record(TokenUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3))
    snap = tracker.snapshot()
    assert snap["total_tokens"] == 3
    assert SECRET_KEY not in json.dumps(snap)


def test_get_provider_builds_from_settings(monkeypatch):
    class FakeSettings:
        llm_provider = "deepseek"
        llm_api_key = SECRET_KEY
        llm_model = "deepseek-v4-pro"
        llm_base_url = "https://api.deepseek.com"
        llm_proxy = "http://127.0.0.1:7890"
        llm_timeout_seconds = 30.0

    provider = get_provider(settings=FakeSettings())
    assert provider.name == "deepseek"
    assert provider.model == "deepseek-v4-pro"
