"""Tests for Fountain parsing + two-stage extraction (llm-extraction spec).

Verifies:
- Character set comes from cue structure, not guessed from action prose.
- Ordinary nouns in action lines are NOT treated as characters.
- The deterministic stage (characters) commits without any LLM call.
- LLM extraction failure / timeout does not block (characters still commit,
  failure recorded, retry possible next time).
- Source spans for facts are located back to the manuscript text.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import ExtractionService, parse_fountain  # noqa: E402
from app.services.fountain import ElementType  # noqa: E402
from app.services.llm_provider import LLMProvider, LLMResponse, TokenUsage  # noqa: E402


# --- Fountain parser tests ---


def test_characters_from_cue_structure():
    text = "INT. 房间 - 日\n\n@小明\n你好。\n\n@小红\n嗨。\n"
    r = parse_fountain(text)
    assert r.characters == ["小明", "小红"]


def test_action_nouns_not_treated_as_characters():
    # "房间" / "夜晚" appear in action prose, never as cues -> not characters.
    text = "INT. 房间 - 日\n\n房间里很安静，夜晚降临。小明走进来。\n\n@小明\n有人吗？\n"
    r = parse_fountain(text)
    assert r.characters == ["小明"]
    assert "房间" not in r.characters
    assert "夜晚" not in r.characters


def test_dialogue_attributed_to_character():
    text = "@小明\n第一句。\n第二句。\n"
    r = parse_fountain(text)
    dialog = [e for e in r.elements if e.type is ElementType.DIALOGUE]
    assert len(dialog) == 2
    assert all(e.character == "小明" for e in dialog)


def test_source_span_locates_text():
    text = "INT. 房间 - 日\n\n@小明\n今天天气真好。\n"
    r = parse_fountain(text)
    for el in r.elements:
        # The cue element's name strips '@', so skip exact-match check for it.
        if el.type is ElementType.CHARACTER:
            continue
        assert text[el.start : el.end] == el.text


def test_latin_allcaps_cue_recognized():
    text = "INT. ROOM - DAY\n\nJOHN\nHello there.\n"
    r = parse_fountain(text)
    assert "JOHN" in r.characters


# --- Extraction service tests ---


class _FakeLLM(LLMProvider):
    def __init__(self, response_text: str):
        super().__init__()
        self._response_text = response_text
        self.calls = 0

    @property
    def name(self):
        return "fake"

    @property
    def model(self):
        return "fake-1"

    def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=None):
        self.calls += 1
        usage = TokenUsage(1, 1, 2)
        self.tracker.record(usage)
        return LLMResponse(text=self._response_text, model=self.model, usage=usage)


class _BoomLLM(LLMProvider):
    def __init__(self):
        super().__init__()
        self.calls = 0

    @property
    def name(self):
        return "boom"

    @property
    def model(self):
        return "boom-1"

    def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=None):
        self.calls += 1
        raise TimeoutError("simulated LLM timeout")


def _characters_in_log(event_log):
    out = []
    for e in event_log.read_events():
        etype = e.type.value if hasattr(e.type, "value") else e.type
        if etype == "character.created":
            out.append(e.payload["name"])
    return out


def test_deterministic_stage_commits_without_llm(event_log_service):
    # No LLM provider at all -> characters still extracted deterministically.
    svc = ExtractionService(event_log_service, llm_provider=None)
    text = "INT. 房间 - 日\n\n@小明\n你好。\n\n@小红\n嗨。\n"
    result = svc.extract(text, revision="rev_1")
    assert result.characters == ["小明", "小红"]
    assert len(result.new_character_ids) == 2
    assert _characters_in_log(event_log_service) == ["小明", "小红"]
    assert result.llm_succeeded is False
    assert result.llm_error == "no_llm_configured"


def test_extraction_failure_does_not_block(event_log_service):
    llm = _BoomLLM()
    svc = ExtractionService(event_log_service, llm_provider=llm)
    text = "INT. 房间 - 日\n\n@小明\n你好。\n"
    result = svc.extract(text, revision="rev_1")
    # LLM was attempted and failed, but characters still committed.
    assert llm.calls == 1
    assert result.llm_succeeded is False
    assert "timeout" in result.llm_error.lower()
    assert _characters_in_log(event_log_service) == ["小明"]
    # No facts were created on failure.
    facts = [
        e
        for e in event_log_service.read_events()
        if (e.type.value if hasattr(e.type, "value") else e.type) == "fact.created"
    ]
    assert facts == []


def test_llm_facts_get_located_source_span(event_log_service):
    text = "INT. 房间 - 日\n\n@小明\n我妹妹昨天去世了。\n"
    response = (
        '{"facts": [{"content": "小明的妹妹去世", '
        '"about_characters": ["小明"], "kind": "event", '
        '"source_quote": "我妹妹昨天去世了。"}]}'
    )
    llm = _FakeLLM(response)
    svc = ExtractionService(event_log_service, llm_provider=llm)
    result = svc.extract(text, revision="rev_1")
    assert result.llm_succeeded is True
    assert len(result.facts) == 1
    fact = result.facts[0]
    # Span must locate the quote back in the manuscript.
    assert text[fact.start : fact.end] == "我妹妹昨天去世了。"


def test_llm_handles_code_fenced_json(event_log_service):
    text = "@小明\n台词。\n"
    response = '```json\n{"facts": []}\n```'
    llm = _FakeLLM(response)
    svc = ExtractionService(event_log_service, llm_provider=llm)
    result = svc.extract(text, revision="rev_1")
    assert result.llm_succeeded is True
    assert result.facts == []


def test_existing_characters_not_duplicated(event_log_service):
    llm = None
    svc = ExtractionService(event_log_service, llm_provider=llm)
    text = "@小明\n第一次。\n"
    svc.extract(text, revision="rev_1")
    # Second extraction with the same character must not re-create it.
    svc.extract("@小明\n第二次。\n", revision="rev_2")
    assert _characters_in_log(event_log_service) == ["小明"]
