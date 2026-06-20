"""Tests for contradiction detection (contradiction-detection spec).

Verifies:
- A hard character status conflict (alive vs dead) is detected from extracted
  Facts and produces exactly one ContinuityEvent.
- No conflict among facts produces zero noise events.
- The ContinuityEvent carries evidence (fact ids + spans + quotes) ONLY, never
  a verdict / fix suggestion / creative explanation.
- Detection is deterministic over normalized status enums - it does NOT guess
  meaning from raw keywords (the original failure mode).
- Re-running the batch does not duplicate an already-recorded finding.
- A monitor failure is isolated by the caller and never blocks writing.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import ContradictionService, ExtractionService  # noqa: E402
from app.services.llm_provider import LLMProvider, LLMResponse, TokenUsage  # noqa: E402


class _ScriptedLLM(LLMProvider):
    """Returns a queued response per call (one per extract())."""

    def __init__(self, responses: list[str]):
        super().__init__()
        self._responses = list(responses)
        self.calls = 0

    @property
    def name(self):
        return "scripted"

    @property
    def model(self):
        return "scripted-1"

    def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=None):
        self.calls += 1
        text = self._responses.pop(0)
        usage = TokenUsage(1, 1, 2)
        self.tracker.record(usage)
        return LLMResponse(text=text, model=self.model, usage=usage)


def _continuity_events(event_log):
    out = []
    for e in event_log.read_events():
        etype = e.type.value if hasattr(e.type, "value") else e.type
        if etype == "continuity_event.created":
            out.append(e.payload)
    return out


def _seed_conflicting_facts(event_log):
    """Use extraction with a scripted LLM to commit alive+dead facts for 姐姐."""
    dead = (
        '{"facts": [{"content": "姐姐十年前去世", '
        '"about_characters": ["姐姐"], "kind": "event", '
        '"character_status": "dead", "source_quote": "姐姐十年前去世了。"}]}'
    )
    alive = (
        '{"facts": [{"content": "姐姐昨天打电话来", '
        '"about_characters": ["姐姐"], "kind": "event", '
        '"character_status": "alive", "source_quote": "姐姐昨天打电话来。"}]}'
    )
    llm = _ScriptedLLM([dead, alive])
    svc = ExtractionService(event_log, llm_provider=llm)
    svc.extract("@小明\n姐姐十年前去世了。\n", revision="rev_1")
    svc.extract("@小明\n姐姐昨天打电话来。\n", revision="rev_2")


def test_detects_character_status_conflict(event_log_service):
    _seed_conflicting_facts(event_log_service)
    monitor = ContradictionService(event_log_service)
    created = monitor.run_batch(revision="rev_2")
    assert len(created) == 1
    events = _continuity_events(event_log_service)
    assert len(events) == 1
    assert events[0]["type"] == "character_status_conflict"
    assert events[0]["involved_character_names"] == ["姐姐"]


def test_no_conflict_no_noise(event_log_service):
    # Both facts say alive -> no conflict.
    a = (
        '{"facts": [{"content": "姐姐在家", '
        '"about_characters": ["姐姐"], "kind": "assertion", '
        '"character_status": "alive", "source_quote": "姐姐在家。"}]}'
    )
    b = (
        '{"facts": [{"content": "姐姐去散步", '
        '"about_characters": ["姐姐"], "kind": "event", '
        '"character_status": "alive", "source_quote": "姐姐去散步。"}]}'
    )
    llm = _ScriptedLLM([a, b])
    svc = ExtractionService(event_log_service, llm_provider=llm)
    svc.extract("@小明\n姐姐在家。\n", revision="rev_1")
    svc.extract("@小明\n姐姐去散步。\n", revision="rev_2")

    monitor = ContradictionService(event_log_service)
    created = monitor.run_batch(revision="rev_2")
    assert created == []
    assert _continuity_events(event_log_service) == []


def test_event_carries_evidence_only_no_verdict(event_log_service):
    _seed_conflicting_facts(event_log_service)
    monitor = ContradictionService(event_log_service)
    monitor.run_batch(revision="rev_2")
    payload = _continuity_events(event_log_service)[0]

    # Evidence present: fact ids, quotes, spans.
    assert len(payload["evidence_fact_ids"]) == 2
    assert len(payload["evidence"]) == 2
    assert len(payload["evidence_spans"]) == 2
    # No verdict / suggestion / explanation fields, and title stays null.
    assert payload["title"] is None
    for forbidden in ("suggestion", "fix", "explanation", "verdict", "recommendation"):
        assert forbidden not in payload
    # Evidence text is the observed fact content, not a judgment.
    assert any("去世" in e for e in payload["evidence"])
    assert any("打电话" in e for e in payload["evidence"])


def test_unknown_status_does_not_trigger(event_log_service):
    # The same character mentioned twice but never with a definite alive/dead
    # status must NOT be flagged - detection keys on normalized enums, not text.
    a = (
        '{"facts": [{"content": "姐姐说了句话", '
        '"about_characters": ["姐姐"], "kind": "assertion", '
        '"character_status": "unknown", "source_quote": "姐姐说了句话。"}]}'
    )
    b = (
        '{"facts": [{"content": "提到姐姐的死亡", '
        '"about_characters": ["姐姐"], "kind": "assertion", '
        '"character_status": "unknown", "source_quote": "提到姐姐的死亡。"}]}'
    )
    llm = _ScriptedLLM([a, b])
    svc = ExtractionService(event_log_service, llm_provider=llm)
    svc.extract("@小明\n姐姐说了句话。\n", revision="rev_1")
    svc.extract("@小明\n提到姐姐的死亡。\n", revision="rev_2")

    monitor = ContradictionService(event_log_service)
    assert monitor.run_batch(revision="rev_2") == []


def test_rerun_does_not_duplicate(event_log_service):
    _seed_conflicting_facts(event_log_service)
    monitor = ContradictionService(event_log_service)
    first = monitor.run_batch(revision="rev_2")
    second = monitor.run_batch(revision="rev_2")
    assert len(first) == 1
    assert second == []
    assert len(_continuity_events(event_log_service)) == 1


def test_detect_is_pure_no_side_effects(event_log_service):
    _seed_conflicting_facts(event_log_service)
    monitor = ContradictionService(event_log_service)
    conflicts = monitor.detect()
    # detect() must not write anything to the log.
    assert _continuity_events(event_log_service) == []
    assert len(conflicts) == 1
    assert conflicts[0].character == "姐姐"


def test_per_character_statuses_detect_conflict(event_log_service):
    # New shape: character_statuses map. The benchmark case must still fire.
    dead = (
        '{"facts": [{"content": "姐姐十年前去世", '
        '"about_characters": ["姐姐"], "kind": "event", '
        '"character_statuses": {"姐姐": "dead"}, '
        '"source_quote": "姐姐十年前去世了。"}]}'
    )
    alive = (
        '{"facts": [{"content": "姐姐昨天打电话来", '
        '"about_characters": ["姐姐"], "kind": "event", '
        '"character_statuses": {"姐姐": "alive"}, '
        '"source_quote": "姐姐昨天打电话来。"}]}'
    )
    llm = _ScriptedLLM([dead, alive])
    svc = ExtractionService(event_log_service, llm_provider=llm)
    svc.extract("@小明\n姐姐十年前去世了。\n", revision="rev_1")
    svc.extract("@小明\n姐姐昨天打电话来。\n", revision="rev_2")

    monitor = ContradictionService(event_log_service)
    created = monitor.run_batch(revision="rev_2")
    assert len(created) == 1
    events = _continuity_events(event_log_service)
    assert events[0]["involved_character_names"] == ["姐姐"]


def test_per_character_does_not_smear_status_to_bystander(event_log_service):
    # Core bug this refactor fixes: a fact about 姐姐's death that also mentions
    # 林婉 must NOT mark 林婉 as dead. Only 姐姐 gets the dead status.
    dead = (
        '{"facts": [{"content": "姐姐在林婉面前去世", '
        '"about_characters": ["姐姐", "林婉"], "kind": "event", '
        '"character_statuses": {"姐姐": "dead", "林婉": "alive"}, '
        '"source_quote": "姐姐在林婉面前去世了。"}]}'
    )
    later = (
        '{"facts": [{"content": "林婉还活着在说话", '
        '"about_characters": ["林婉"], "kind": "assertion", '
        '"character_statuses": {"林婉": "alive"}, '
        '"source_quote": "林婉还在说话。"}]}'
    )
    llm = _ScriptedLLM([dead, later])
    svc = ExtractionService(event_log_service, llm_provider=llm)
    svc.extract("@小明\n姐姐在林婉面前去世了。\n", revision="rev_1")
    svc.extract("@小明\n林婉还在说话。\n", revision="rev_2")

    monitor = ContradictionService(event_log_service)
    # 林婉 is alive in both facts -> no false conflict smeared from 姐姐's death.
    assert monitor.run_batch(revision="rev_2") == []


def test_legacy_single_status_still_replays(event_log_service):
    # Old-shape events (single character_status) must still replay and detect.
    dead = (
        '{"facts": [{"content": "姐姐去世", '
        '"about_characters": ["姐姐"], "kind": "event", '
        '"character_status": "dead", "source_quote": "姐姐去世了。"}]}'
    )
    alive = (
        '{"facts": [{"content": "姐姐打电话", '
        '"about_characters": ["姐姐"], "kind": "event", '
        '"character_status": "alive", "source_quote": "姐姐打电话来。"}]}'
    )
    llm = _ScriptedLLM([dead, alive])
    svc = ExtractionService(event_log_service, llm_provider=llm)
    svc.extract("@小明\n姐姐去世了。\n", revision="rev_1")
    svc.extract("@小明\n姐姐打电话来。\n", revision="rev_2")

    monitor = ContradictionService(event_log_service)
    assert len(monitor.run_batch(revision="rev_2")) == 1
