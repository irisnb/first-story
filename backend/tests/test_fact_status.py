"""Tests for Fact acceptance_status / source_type migration (tasks group 3).

Verifies:
- New facts can carry candidate/chat values.
- Historical facts (payload missing the fields) read back as committed+document.
- The two status dimensions are orthogonal and vary independently.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import Fact  # noqa: E402
from app.models.common import (  # noqa: E402
    FactAcceptanceStatus,
    FactLifecycleStatus,
    FactSourceType,
)


def _base_fact_kwargs(**overrides):
    kwargs = dict(
        id="fact_1",
        content="主角有个妹妹",
        source_event_id="evt_1",
        source_document_id="main",
        source_revision="rev_1",
        source_span={"start": 0, "end": 5},
        source_text_hash="hash",
        extraction_confidence=0.7,
    )
    kwargs.update(overrides)
    return kwargs


def test_fact_defaults_to_committed_document():
    """A fact built without the new fields is committed + document + active."""
    fact = Fact(**_base_fact_kwargs())
    assert fact.acceptance_status == FactAcceptanceStatus.COMMITTED
    assert fact.source_type == FactSourceType.DOCUMENT
    assert fact.lifecycle_status == FactLifecycleStatus.ACTIVE


def test_fact_accepts_candidate_chat():
    fact = Fact(
        **_base_fact_kwargs(
            acceptance_status="candidate",
            source_type="chat",
        )
    )
    assert fact.acceptance_status == FactAcceptanceStatus.CANDIDATE
    assert fact.source_type == FactSourceType.CHAT
    # Lifecycle is untouched - still active.
    assert fact.lifecycle_status == FactLifecycleStatus.ACTIVE


def test_acceptance_and_lifecycle_are_orthogonal():
    """active+committed, active+candidate, retracted+committed all expressible."""
    a = Fact(**_base_fact_kwargs(acceptance_status="committed", lifecycle_status="active"))
    b = Fact(**_base_fact_kwargs(acceptance_status="candidate", lifecycle_status="active"))
    c = Fact(**_base_fact_kwargs(acceptance_status="committed", lifecycle_status="retracted"))
    assert (a.acceptance_status, a.lifecycle_status) == (
        FactAcceptanceStatus.COMMITTED,
        FactLifecycleStatus.ACTIVE,
    )
    assert (b.acceptance_status, b.lifecycle_status) == (
        FactAcceptanceStatus.CANDIDATE,
        FactLifecycleStatus.ACTIVE,
    )
    assert (c.acceptance_status, c.lifecycle_status) == (
        FactAcceptanceStatus.COMMITTED,
        FactLifecycleStatus.RETRACTED,
    )


def test_projector_applies_historical_defaults(event_log_service, projector_service):
    """A fact.created payload missing the new fields projects as committed+document."""
    from app.services.hub import get_hub

    writer = get_hub().writer_for(event_log_service)
    writer.append(
        event_id="evt_fact_old",
        idempotency_key="k_old",
        event_type="fact.created",
        payload={
            "fact_id": "fact_old",
            "content": "老数据没有新字段",
            "about_character_ids": [],
            "source_document_id": "main",
            "source_revision": "rev_old",
            "source_span": {"start": 0, "end": 4},
            "source_text_hash": "h",
            "extraction_confidence": 0.6,
            # NOTE: no acceptance_status / source_type / lifecycle_status
        },
        actor="extraction_agent",
    )
    state = projector_service.rebuild()
    facts = [f for f in state.story.facts if f.id == "fact_old"]
    assert len(facts) == 1
    assert facts[0].acceptance_status == FactAcceptanceStatus.COMMITTED
    assert facts[0].source_type == FactSourceType.DOCUMENT
    assert facts[0].lifecycle_status == FactLifecycleStatus.ACTIVE


def test_projector_preserves_candidate_chat(event_log_service, projector_service):
    from app.services.hub import get_hub

    writer = get_hub().writer_for(event_log_service)
    writer.append(
        event_id="evt_fact_cand",
        idempotency_key="k_cand",
        event_type="fact.created",
        payload={
            "fact_id": "fact_cand",
            "content": "聊天里随口提的设定",
            "about_character_ids": [],
            "source_document_id": "main",
            "source_revision": "rev_cand",
            "source_span": {"start": 0, "end": 4},
            "source_text_hash": "h",
            "extraction_confidence": 0.6,
            "acceptance_status": "candidate",
            "source_type": "chat",
        },
        actor="dialogue_gateway",
    )
    state = projector_service.rebuild()
    facts = [f for f in state.story.facts if f.id == "fact_cand"]
    assert len(facts) == 1
    assert facts[0].acceptance_status == FactAcceptanceStatus.CANDIDATE
    assert facts[0].source_type == FactSourceType.CHAT
