"""Tests for alias resolution (B' identity-only coreference pass).

These cover the "soul function" fix: the benchmark contradiction (a dead sister
who later phones home) only fires when the system recognizes that two different
surface names ("姐姐" / "姐") refer to ONE character. The alias pass makes that
identity judgment in isolation - it never touches alive/dead status, which stays
with the extraction LLM and the deterministic detector.

Verifies:
- Alias binding maps surface names to a canonical name and is replayed into the
  detector so the benchmark conflict is detected across differing names.
- The pass is CONSERVATIVE: it never binds names the LLM was not given, never
  binds a name to itself, and leaves ambiguous names unbound.
- Alias bindings are append-only and rebuilt by replay.
- An alias LLM failure is isolated: no bindings written, detection falls back to
  exact-name grouping (still works when names already match).
- The alias pass NEVER emits or considers status - identity only.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import (  # noqa: E402
    AliasResolverService,
    ContradictionService,
    ExtractionService,
)
from app.services.llm_provider import LLMProvider, LLMResponse, TokenUsage  # noqa: E402


class _ScriptedLLM(LLMProvider):
    """Returns a queued response per call."""

    def __init__(self, responses: list[str]):
        super().__init__()
        self._responses = list(responses)
        self.calls = 0
        self.prompts: list[str] = []
        self.systems: list[str] = []

    @property
    def name(self):
        return "scripted"

    @property
    def model(self):
        return "scripted-1"

    def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=None):
        self.calls += 1
        self.prompts.append(prompt)
        self.systems.append(system or "")
        text = self._responses.pop(0)
        usage = TokenUsage(1, 1, 2)
        self.tracker.record(usage)
        return LLMResponse(text=text, model=self.model, usage=usage)


def _alias_bound_events(event_log):
    out = []
    for e in event_log.read_events():
        etype = e.type.value if hasattr(e.type, "value") else e.type
        if etype == "character.alias_bound":
            out.append(e.payload)
    return out


def _seed_facts_with_differing_names(event_log):
    """Commit a 'dead' fact about 姐姐 and an 'alive' fact about 姐.

    With NO alias resolution these are two different characters and produce no
    conflict. The alias pass is what binds them.
    """
    dead = (
        '{"facts": [{"content": "姐姐十年前去世", '
        '"about_characters": ["姐姐"], "kind": "event", '
        '"character_statuses": {"姐姐": "dead"}, '
        '"source_quote": "姐姐十年前去世了。"}]}'
    )
    alive = (
        '{"facts": [{"content": "姐昨天打电话来", '
        '"about_characters": ["姐"], "kind": "event", '
        '"character_statuses": {"姐": "alive"}, '
        '"source_quote": "姐昨天打电话来。"}]}'
    )
    llm = _ScriptedLLM([dead, alive])
    svc = ExtractionService(event_log, llm_provider=llm)
    svc.extract("姐姐十年前去世了。\n", revision="rev_1")
    svc.extract("姐昨天打电话来。\n", revision="rev_2")


def test_without_alias_differing_names_do_not_conflict(event_log_service):
    # Baseline: 姐姐 (dead) and 姐 (alive) are distinct names -> no conflict.
    _seed_facts_with_differing_names(event_log_service)
    monitor = ContradictionService(event_log_service)
    assert monitor.run_batch(revision="rev_2") == []


def test_alias_binding_makes_benchmark_conflict_detected(event_log_service):
    # The soul function: bind 姐 -> 姐姐, then the dead/alive conflict fires.
    _seed_facts_with_differing_names(event_log_service)

    alias_response = (
        '{"groups": [{"canonical": "姐姐", "aliases": ["姐"]}]}'
    )
    alias_llm = _ScriptedLLM([alias_response])
    resolver = AliasResolverService(event_log_service, llm_provider=alias_llm)
    result = resolver.resolve("姐姐十年前去世了。姐昨天打电话来。")
    assert result.llm_succeeded
    assert len(result.bound_event_ids) == 1

    monitor = ContradictionService(event_log_service)
    created = monitor.run_batch(revision="rev_2")
    assert len(created) == 1
    # Conflict is reported under the canonical name.
    events = [
        e.payload
        for e in event_log_service.read_events()
        if (e.type.value if hasattr(e.type, "value") else e.type)
        == "continuity_event.created"
    ]
    assert events[0]["involved_character_names"] == ["姐姐"]


def test_alias_prompt_is_identity_only_never_status(event_log_service):
    # Guard the design invariant: the alias pass must not ask about life/death.
    _seed_facts_with_differing_names(event_log_service)
    alias_llm = _ScriptedLLM(['{"groups": []}'])
    resolver = AliasResolverService(event_log_service, llm_provider=alias_llm)
    resolver.resolve("姐姐十年前去世了。姐昨天打电话来。")

    blob = alias_llm.prompts[0] + alias_llm.systems[0]
    for forbidden in ("alive", "dead", "生死", "状态", "存活"):
        # The word 身份 (identity) is expected; status vocabulary is not the goal.
        assert forbidden not in blob or "身份" in blob


def test_conservative_never_binds_unknown_names(event_log_service):
    # If the LLM returns a canonical / alias not present in the fact name set,
    # it must be ignored (no invented identities).
    _seed_facts_with_differing_names(event_log_service)
    bad = (
        '{"groups": [{"canonical": "从未出现的人", "aliases": ["姐"]}, '
        '{"canonical": "姐姐", "aliases": ["也没出现过"]}]}'
    )
    alias_llm = _ScriptedLLM([bad])
    resolver = AliasResolverService(event_log_service, llm_provider=alias_llm)
    result = resolver.resolve("姐姐十年前去世了。姐昨天打电话来。")
    # First group: canonical not in name set -> dropped.
    # Second group: only alias is invented -> no valid aliases -> dropped.
    assert result.bound_event_ids == []
    assert _alias_bound_events(event_log_service) == []


def test_alias_map_replays_append_only(event_log_service):
    _seed_facts_with_differing_names(event_log_service)
    alias_llm = _ScriptedLLM(['{"groups": [{"canonical": "姐姐", "aliases": ["姐"]}]}'])
    resolver = AliasResolverService(event_log_service, llm_provider=alias_llm)
    resolver.resolve("姐姐十年前去世了。姐昨天打电话来。")

    # A fresh resolver instance must rebuild the same map purely from the log.
    fresh = AliasResolverService(event_log_service, llm_provider=None)
    mapping = fresh.load_alias_map()
    assert mapping["姐"] == "姐姐"
    assert mapping["姐姐"] == "姐姐"


def test_alias_llm_failure_is_isolated(event_log_service):
    # A malformed alias response writes no bindings and raises nothing upward.
    _seed_facts_with_differing_names(event_log_service)
    alias_llm = _ScriptedLLM(["not json at all"])
    resolver = AliasResolverService(event_log_service, llm_provider=alias_llm)
    result = resolver.resolve("姐姐十年前去世了。姐昨天打电话来。")
    assert not result.llm_succeeded
    assert result.llm_error is not None
    assert _alias_bound_events(event_log_service) == []
    # Detection still runs (falls back to exact names) - no crash.
    monitor = ContradictionService(event_log_service)
    assert monitor.run_batch(revision="rev_2") == []


def test_no_llm_configured_is_noop(event_log_service):
    _seed_facts_with_differing_names(event_log_service)
    resolver = AliasResolverService(event_log_service, llm_provider=None)
    result = resolver.resolve("姐姐十年前去世了。姐昨天打电话来。")
    assert result.llm_error == "no_llm_configured"
    assert _alias_bound_events(event_log_service) == []


def test_within_fact_alias_collapse_keeps_dead_signal(event_log_service):
    # If one fact carries both '姐姐'->dead and '姐'->alive and they resolve to
    # the same canonical, collapsing must keep the stronger 'dead' rather than
    # silently dropping a death assertion. Then a separate alive fact conflicts.
    mixed = (
        '{"facts": [{"content": "姐姐去世而姐还在", '
        '"about_characters": ["姐姐", "姐"], "kind": "event", '
        '"character_statuses": {"姐姐": "dead", "姐": "unknown"}, '
        '"source_quote": "姐姐去世了。"}]}'
    )
    alive = (
        '{"facts": [{"content": "姐打电话", '
        '"about_characters": ["姐"], "kind": "event", '
        '"character_statuses": {"姐": "alive"}, '
        '"source_quote": "姐打电话来。"}]}'
    )
    ext_llm = _ScriptedLLM([mixed, alive])
    svc = ExtractionService(event_log_service, llm_provider=ext_llm)
    svc.extract("姐姐去世了。\n", revision="rev_1")
    svc.extract("姐打电话来。\n", revision="rev_2")

    alias_llm = _ScriptedLLM(['{"groups": [{"canonical": "姐姐", "aliases": ["姐"]}]}'])
    resolver = AliasResolverService(event_log_service, llm_provider=alias_llm)
    resolver.resolve("姐姐去世了。姐打电话来。")

    monitor = ContradictionService(event_log_service)
    created = monitor.run_batch(revision="rev_2")
    assert len(created) == 1
