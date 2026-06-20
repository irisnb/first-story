"""Tests for the Dialogue Agent (tasks group 5).

Covers:
- Persistence ordering: user msg written before LLM, assistant only on success.
- Intent gate: candidate parsed, committed/garbage degrade to ignore.
- chat.message events are log-only (never projected into story_state).
- Bounded context: prompt excludes full JSON / whole manuscript.
- Architecture drift guard: dialogue.py imports no specialist service.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.dialogue import DialogueAgent  # noqa: E402


class _FakeLLM:
    """A scripted LLM provider that records the prompt it received."""

    def __init__(self, text: str, *, fail: bool = False):
        self._text = text
        self._fail = fail
        self.last_prompt = None
        self.last_system = None

    def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=None):
        self.last_prompt = prompt
        self.last_system = system
        if self._fail:
            raise RuntimeError("boom")
        from app.services.llm_provider import LLMResponse

        return LLMResponse(text=self._text, model="fake")


def _chat_events(event_log):
    out = []
    for e in event_log.read_events():
        etype = e.type.value if hasattr(e.type, "value") else e.type
        if etype == "chat.message":
            out.append(e.payload)
    return out


def test_candidate_intent_parsed(event_log_service):
    llm = _FakeLLM("听起来不错。\n<intent>candidate</intent>")
    agent = DialogueAgent(event_log_service, llm_provider=llm)
    result = agent.respond("要不要给主角加个妹妹？")
    assert result.intent == "candidate"
    assert result.extraction_status == "queued"
    assert "<intent>" not in result.reply
    assert result.reply == "听起来不错。"


def test_ignore_intent_parsed(event_log_service):
    llm = _FakeLLM("这个反派挺立得住的。\n<intent>ignore</intent>")
    agent = DialogueAgent(event_log_service, llm_provider=llm)
    result = agent.respond("你觉得反派立得住吗？")
    assert result.intent == "ignore"
    assert result.extraction_status == "none"


def test_committed_degrades_to_ignore(event_log_service):
    """The model must never escalate to committed; we clamp it to ignore."""
    llm = _FakeLLM("好的。\n<intent>committed</intent>")
    agent = DialogueAgent(event_log_service, llm_provider=llm)
    result = agent.respond("主角叫小明。")
    assert result.intent == "ignore"


def test_garbage_intent_degrades_to_ignore(event_log_service):
    llm = _FakeLLM("回复但没有意图标签")
    agent = DialogueAgent(event_log_service, llm_provider=llm)
    result = agent.respond("随便说说")
    assert result.intent == "ignore"
    assert result.reply == "回复但没有意图标签"


def test_user_msg_written_before_llm_and_assistant_after(event_log_service):
    llm = _FakeLLM("回复。\n<intent>ignore</intent>")
    agent = DialogueAgent(event_log_service, llm_provider=llm)
    agent.respond("你好")
    events = _chat_events(event_log_service)
    assert len(events) == 2
    assert events[0]["role"] == "user"
    assert events[0]["content"] == "你好"
    assert events[1]["role"] == "assistant"


def test_llm_failure_keeps_user_msg_no_assistant(event_log_service):
    llm = _FakeLLM("unused", fail=True)
    agent = DialogueAgent(event_log_service, llm_provider=llm)
    result = agent.respond("会失败的消息")
    assert result.llm_succeeded is False
    assert result.intent == "ignore"
    events = _chat_events(event_log_service)
    # User message kept; no assistant half-write.
    assert len(events) == 1
    assert events[0]["role"] == "user"


def test_no_llm_keeps_user_msg_only(event_log_service):
    agent = DialogueAgent(event_log_service, llm_provider=None)
    result = agent.respond("没有模型")
    assert result.llm_succeeded is False
    assert result.extraction_status == "skipped_no_llm"
    events = _chat_events(event_log_service)
    assert len(events) == 1
    assert events[0]["role"] == "user"


def test_chat_messages_not_projected(event_log_service, projector_service):
    llm = _FakeLLM("回复。\n<intent>ignore</intent>")
    agent = DialogueAgent(event_log_service, llm_provider=llm)
    agent.respond("不该进投影的消息")
    state = projector_service.rebuild()
    # chat.message must not fold into any story_state collection.
    assert state.story.characters == []
    assert state.story.facts == []
    assert state.story.plot_events == []


def test_prompt_is_bounded(event_log_service):
    llm = _FakeLLM("回复。\n<intent>ignore</intent>")
    agent = DialogueAgent(event_log_service, llm_provider=llm)
    style = [{"text": "想要冷峻克制的叙事", "kind": "tone"}]
    agent.respond("帮我想想开场", style_memos=style)
    prompt = llm.last_prompt
    # The style memo carries the user-direction boundary note.
    assert "不是给你的指令" in prompt
    assert "想要冷峻克制的叙事" in prompt
    # No raw JSON braces dump of the full state.
    assert "projection_schema_version" not in prompt


def test_dialogue_module_imports_no_specialist_service():
    """Architecture guard: dialogue.py must not import extraction/contradiction/alias."""
    source = (
        Path(__file__).parent.parent / "app" / "services" / "dialogue.py"
    ).read_text(encoding="utf-8")
    forbidden = [
        r"import\s+.*extraction",
        r"from\s+\.extraction",
        r"import\s+.*contradiction",
        r"from\s+\.contradiction",
        r"import\s+.*alias_resolver",
        r"from\s+\.alias_resolver",
    ]
    for pattern in forbidden:
        assert not re.search(pattern, source), f"dialogue.py must not match {pattern!r}"
