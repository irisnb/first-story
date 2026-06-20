"""Tests for document revision (document-revision spec).

Verifies:
- Saving creates a new revision recorded on the event log.
- Multiple saves keep every historical revision (no overwrite).
- Restoring an old revision appends a NEW revision (growth, not deletion).
- Rebuilt projection reflects the latest revision.
- source span locates the revision content back to the document.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import compute_text_hash  # noqa: E402
from app.services import DocumentService  # noqa: E402


@pytest.fixture
def document_service(event_log_service):
    return DocumentService(event_log_service)


def test_save_creates_revision(document_service):
    rev = document_service.save_revision("INT. 房间 - 日\n\n小明走进来。")
    assert rev.revision_id.startswith("rev_")
    assert rev.source_event_id.startswith("evt_")
    assert rev.content_hash == compute_text_hash(rev.content)


def test_save_records_on_event_log(document_service, event_log_service):
    document_service.save_revision("第一版正文")
    events = [
        e
        for e in event_log_service.read_events()
        if (e.type.value if hasattr(e.type, "value") else e.type) == "document.revised"
    ]
    assert len(events) == 1
    assert events[0].payload["content"] == "第一版正文"


def test_multiple_saves_keep_history(document_service):
    document_service.save_revision("版本一")
    document_service.save_revision("版本二")
    document_service.save_revision("版本三")
    revisions = document_service.list_revisions()
    assert len(revisions) == 3
    # Oldest first; no version is overwritten.
    assert [r.content for r in revisions] == ["版本一", "版本二", "版本三"]


def test_revisions_have_distinct_ids(document_service):
    r1 = document_service.save_revision("a")
    r2 = document_service.save_revision("b")
    assert r1.revision_id != r2.revision_id


def test_restore_appends_new_revision(document_service):
    r1 = document_service.save_revision("原始正文")
    document_service.save_revision("后来改坏了")
    restored = document_service.restore_revision(r1.revision_id)
    assert restored is not None
    assert restored.content == "原始正文"
    assert restored.restored_from_revision_id == r1.revision_id
    # Restore is growth: original 2 + 1 restore = 3 revisions, nothing deleted.
    revisions = document_service.list_revisions()
    assert len(revisions) == 3
    assert revisions[0].content == "原始正文"  # original still present
    assert revisions[-1].content == "原始正文"  # restored copy at the end


def test_restore_missing_revision_returns_none(document_service):
    document_service.save_revision("x")
    assert document_service.restore_revision("rev_doesnotexist") is None


def test_rebuild_reflects_latest_revision(document_service, projector_service):
    document_service.save_revision("旧正文")
    document_service.save_revision("新正文")
    state = projector_service.rebuild()
    assert state.story.current_document is not None
    assert state.story.current_document.content == "新正文"


def test_replay_after_restore_yields_restored_content(
    document_service, projector_service
):
    r1 = document_service.save_revision("要恢复的正文")
    document_service.save_revision("中间版本")
    document_service.restore_revision(r1.revision_id)
    # Rebuild purely by replaying events - no LLM, no cached shortcut.
    state = projector_service.rebuild()
    assert state.story.current_document.content == "要恢复的正文"


def test_source_span_covers_content(document_service):
    content = "INT. 咖啡馆 - 夜\n\n对白若干。"
    rev = document_service.save_revision(content)
    assert rev.source_span.start == 0
    assert rev.source_span.end == len(content)
    # span end can index back into the document text.
    assert content[rev.source_span.start : rev.source_span.end] == content
