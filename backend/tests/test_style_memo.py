"""Tests for style-memo projection (tasks group 6, creative-memory spec).

Verifies:
- creative_intent.added projects an active StyleMemo, level with the modules.
- creative_intent.archived marks status archived without erasing the log.
- kind falls back to "未分类" when omitted.
- style memos never appear as facts/characters (not in contradiction scope).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.hub import get_hub  # noqa: E402


def test_creative_intent_added_projects_active_memo(event_log_service, projector_service):
    writer = get_hub().writer_for(event_log_service)
    writer.append(
        event_id="evt_memo1",
        idempotency_key="k_memo1",
        event_type="creative_intent.added",
        payload={"memo_id": "memo_1", "text": "动画+collage 拼贴感", "kind": "form"},
        actor="user",
    )
    state = projector_service.rebuild()
    assert len(state.story.style_memos) == 1
    memo = state.story.style_memos[0]
    assert memo.id == "memo_1"
    assert memo.text == "动画+collage 拼贴感"
    assert memo.kind == "form"
    assert memo.status == "active"


def test_kind_defaults_to_uncategorized(event_log_service, projector_service):
    writer = get_hub().writer_for(event_log_service)
    writer.append(
        event_id="evt_memo2",
        idempotency_key="k_memo2",
        event_type="creative_intent.added",
        payload={"memo_id": "memo_2", "text": "冷峻克制"},
        actor="user",
    )
    state = projector_service.rebuild()
    assert state.story.style_memos[0].kind == "未分类"


def test_archive_marks_not_deletes(event_log_service, projector_service):
    writer = get_hub().writer_for(event_log_service)
    writer.append(
        event_id="evt_memo3",
        idempotency_key="k_memo3",
        event_type="creative_intent.added",
        payload={"memo_id": "memo_3", "text": "手持纪实感", "kind": "tone"},
        actor="user",
    )
    writer.append(
        event_id="evt_memo3_arch",
        idempotency_key="k_memo3_arch",
        event_type="creative_intent.archived",
        payload={"memo_id": "memo_3"},
        actor="user",
    )
    state = projector_service.rebuild()
    # Still present (archived, not deleted).
    assert len(state.story.style_memos) == 1
    assert state.story.style_memos[0].status == "archived"


def test_style_memos_not_in_module_collections(event_log_service, projector_service):
    writer = get_hub().writer_for(event_log_service)
    writer.append(
        event_id="evt_memo4",
        idempotency_key="k_memo4",
        event_type="creative_intent.added",
        payload={"memo_id": "memo_4", "text": "梦境逻辑"},
        actor="user",
    )
    state = projector_service.rebuild()
    # A style memo is creative direction, never a fact/character.
    assert state.story.facts == []
    assert state.story.characters == []
    assert len(state.story.style_memos) == 1
