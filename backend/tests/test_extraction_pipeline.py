"""Tests for the shared extraction pipeline (tasks group 4).

Verifies the two lanes diverge correctly:
- committed/document lane: full pass (facts + characters + batch commit), facts
  stamped committed+document.
- candidate/chat lane: idea-record only - facts stamped candidate+chat, NO
  character.created / batch.committed events, alias pass skipped, and the facts
  never enter contradiction detection.

These run hermetically (no LLM key), so only the deterministic Fountain stage
produces character events; the LLM fact stage is short-circuited. We therefore
assert the entity-event behavior (the part the pipeline controls), and use a
direct fact.created round-trip to assert the candidate filter in detection.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import run_extraction_pipeline  # noqa: E402
from app.services.contradiction import ContradictionService  # noqa: E402
from app.services.hub import get_hub  # noqa: E402


def _event_types(event_log) -> list[str]:
    out = []
    for e in event_log.read_events():
        out.append(e.type.value if hasattr(e.type, "value") else e.type)
    return out


def test_committed_lane_writes_batch_commit(project_service, sample_project):
    """Editor prose lane commits the batch (committed-world boundary)."""
    content = "标题: 测试\n\n小明\n你好。\n"
    run_extraction_pipeline(
        project_service,
        sample_project.id,
        content=content,
        source_type="document",
        source_id="rev_1",
        acceptance_status="committed",
    )
    event_log = project_service.get_services(sample_project.id)[0]
    types = _event_types(event_log)
    assert "batch.committed" in types


def test_candidate_lane_skips_entity_events(project_service, sample_project):
    """Chat brainstorm lane is an idea record: no character/batch events."""
    content = "标题: 测试\n\n小红\n随便聊聊。\n"
    run_extraction_pipeline(
        project_service,
        sample_project.id,
        content=content,
        source_type="chat",
        source_id="msg_1",
        acceptance_status="candidate",
    )
    event_log = project_service.get_services(sample_project.id)[0]
    types = _event_types(event_log)
    assert "character.created" not in types
    assert "batch.committed" not in types


def test_candidate_facts_excluded_from_detection(event_log_service):
    """A candidate fact never participates in contradiction detection."""
    writer = get_hub().writer_for(event_log_service)
    # Committed: character dead.
    writer.append(
        event_id="evt_dead",
        idempotency_key="k_dead",
        event_type="fact.created",
        payload={
            "fact_id": "f_dead",
            "content": "阿强死了",
            "about_character_names": ["阿强"],
            "character_statuses": {"阿强": "dead"},
            "source_span": {"start": 0, "end": 3},
            "acceptance_status": "committed",
            "source_type": "document",
        },
        actor="extraction_agent",
    )
    # Candidate: same character alive - a brainstorm, must NOT conflict.
    writer.append(
        event_id="evt_alive_cand",
        idempotency_key="k_alive_cand",
        event_type="fact.created",
        payload={
            "fact_id": "f_alive_cand",
            "content": "如果阿强还活着呢",
            "about_character_names": ["阿强"],
            "character_statuses": {"阿强": "alive"},
            "source_span": {"start": 0, "end": 6},
            "acceptance_status": "candidate",
            "source_type": "chat",
        },
        actor="dialogue_gateway",
    )
    conflicts = ContradictionService(event_log_service).detect()
    assert conflicts == []


def test_two_committed_facts_still_conflict(event_log_service):
    """Sanity: two committed alive/dead facts DO conflict (filter not too broad)."""
    writer = get_hub().writer_for(event_log_service)
    writer.append(
        event_id="evt_dead2",
        idempotency_key="k_dead2",
        event_type="fact.created",
        payload={
            "fact_id": "f_dead2",
            "content": "阿强死了",
            "about_character_names": ["阿强"],
            "character_statuses": {"阿强": "dead"},
            "source_span": {"start": 0, "end": 3},
            "acceptance_status": "committed",
            "source_type": "document",
        },
        actor="extraction_agent",
    )
    writer.append(
        event_id="evt_alive2",
        idempotency_key="k_alive2",
        event_type="fact.created",
        payload={
            "fact_id": "f_alive2",
            "content": "阿强还活着",
            "about_character_names": ["阿强"],
            "character_statuses": {"阿强": "alive"},
            "source_span": {"start": 0, "end": 5},
            "acceptance_status": "committed",
            "source_type": "document",
        },
        actor="extraction_agent",
    )
    conflicts = ContradictionService(event_log_service).detect()
    assert len(conflicts) == 1
    assert conflicts[0].character == "阿强"
