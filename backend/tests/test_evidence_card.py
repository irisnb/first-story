"""Tests for evidence card handling (evidence-card-handling spec).

Verifies:
- Ignoring a card records an append-only ignored event; the original finding
  and facts are never deleted.
- Ignoring a *category* writes a de-weighting rule to project preferences -
  detection is NOT disabled, only future findings are lowered in priority.
- The de-weighting rule and history survive (append-only) and the same
  continuity detection still produces findings afterward.
- Accepting a card marks it resolved while keeping the event record.
- Acting on a non-existent card returns None (404 at the API layer).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import (  # noqa: E402
    ContradictionService,
    EvidenceCardService,
    ExtractionService,
)
from app.services.llm_provider import LLMProvider, LLMResponse, TokenUsage  # noqa: E402


class _ScriptedLLM(LLMProvider):
    def __init__(self, responses):
        super().__init__()
        self._responses = list(responses)

    @property
    def name(self):
        return "scripted"

    @property
    def model(self):
        return "scripted-1"

    def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=None):
        text = self._responses.pop(0)
        usage = TokenUsage(1, 1, 2)
        self.tracker.record(usage)
        return LLMResponse(text=text, model=self.model, usage=usage)


def _events_of(event_log, etype):
    out = []
    for e in event_log.read_events():
        t = e.type.value if hasattr(e.type, "value") else e.type
        if t == etype:
            out.append(e.payload)
    return out


def _seed_one_conflict(event_log):
    dead = (
        '{"facts": [{"content": "姐姐去世", "about_characters": ["姐姐"], '
        '"kind": "event", "character_status": "dead", '
        '"source_quote": "姐姐去世了。"}]}'
    )
    alive = (
        '{"facts": [{"content": "姐姐打电话", "about_characters": ["姐姐"], '
        '"kind": "event", "character_status": "alive", '
        '"source_quote": "姐姐打电话来。"}]}'
    )
    llm = _ScriptedLLM([dead, alive])
    svc = ExtractionService(event_log, llm_provider=llm)
    svc.extract("@小明\n姐姐去世了。\n", revision="rev_1")
    svc.extract("@小明\n姐姐打电话来。\n", revision="rev_2")
    monitor = ContradictionService(event_log)
    created = monitor.run_batch(revision="rev_2")
    return created[0]


def test_ignore_records_event_without_deleting(event_log_service):
    ce_id = _seed_one_conflict(event_log_service)
    facts_before = len(_events_of(event_log_service, "fact.created"))
    ce_before = len(_events_of(event_log_service, "continuity_event.created"))

    svc = EvidenceCardService(event_log_service)
    result = svc.ignore(ce_id, user_explanation="这是有意的鬼故事设定")
    assert result is not None
    assert result.action == "ignored"
    assert result.deweighting_written is False

    ignored = _events_of(event_log_service, "continuity_event.ignored")
    assert len(ignored) == 1
    assert ignored[0]["continuity_event_id"] == ce_id
    # Original facts + finding preserved (append-only).
    assert len(_events_of(event_log_service, "fact.created")) == facts_before
    assert len(_events_of(event_log_service, "continuity_event.created")) == ce_before


def test_ignore_category_writes_deweighting(event_log_service):
    ce_id = _seed_one_conflict(event_log_service)
    svc = EvidenceCardService(event_log_service)
    result = svc.ignore(ce_id, user_explanation="先锋写法", scope="category")
    assert result.deweighting_written is True
    assert result.category == "character_status_conflict"

    deweights = _events_of(event_log_service, "project_preference.deweighting_set")
    assert len(deweights) == 1
    assert deweights[0]["category"] == "character_status_conflict"
    # Lower priority (negative delta), NOT a disable flag.
    assert deweights[0]["weight_delta"] < 0


def test_deweighting_does_not_disable_detection(event_log_service):
    ce_id = _seed_one_conflict(event_log_service)
    svc = EvidenceCardService(event_log_service)
    svc.ignore(ce_id, scope="category")

    # Add a fresh, different conflict; detection MUST still fire.
    dead = (
        '{"facts": [{"content": "哥哥死了", "about_characters": ["哥哥"], '
        '"kind": "event", "character_status": "dead", '
        '"source_quote": "哥哥死了。"}]}'
    )
    alive = (
        '{"facts": [{"content": "哥哥还活着", "about_characters": ["哥哥"], '
        '"kind": "event", "character_status": "alive", '
        '"source_quote": "哥哥还活着。"}]}'
    )
    llm = _ScriptedLLM([dead, alive])
    ext = ExtractionService(event_log_service, llm_provider=llm)
    ext.extract("@旁白\n哥哥死了。\n", revision="rev_3")
    ext.extract("@旁白\n哥哥还活着。\n", revision="rev_4")

    monitor = ContradictionService(event_log_service)
    created = monitor.run_batch(revision="rev_4")
    # New conflict for 哥哥 still detected despite the de-weighting rule.
    assert len(created) == 1


def test_accept_marks_resolved_keeps_record(event_log_service):
    ce_id = _seed_one_conflict(event_log_service)
    ce_before = len(_events_of(event_log_service, "continuity_event.created"))

    svc = EvidenceCardService(event_log_service)
    result = svc.accept(ce_id)
    assert result.action == "accepted"

    resolved = _events_of(event_log_service, "continuity_event.resolved")
    assert len(resolved) == 1
    assert resolved[0]["continuity_event_id"] == ce_id
    # Original finding record kept.
    assert len(_events_of(event_log_service, "continuity_event.created")) == ce_before


def test_action_on_missing_card_returns_none(event_log_service):
    svc = EvidenceCardService(event_log_service)
    assert svc.ignore("ce_does_not_exist") is None
    assert svc.accept("ce_does_not_exist") is None
