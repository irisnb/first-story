"""Tests for the Thin Runtime Hub (agent-hub spec, design D1/D8).

Covers:
- Routing correctness + structured results.
- Background handler failures are isolated (never raised to caller).
- dispatch return values carry NO user-facing natural-language fields.
- Concurrent writes to the same project are serialized (no duplicate seq).
- Existing write paths go through the Hub-cached event log.
- Different projects do not block each other.
- Architecture test: no business code calls append_event() directly except
  event_log.py and hub.py.
"""

import sys
import threading
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.hub import Hub, HubEvent, HubResult, get_hub  # noqa: E402


# ----------------------------------------------------------------- routing


def test_dispatch_routes_to_registered_handler():
    hub = Hub()
    hub.register("test.echo", lambda e: {"got": e.payload.get("x")})
    result = hub.dispatch(HubEvent(type="test.echo", project_id="p1", payload={"x": 7}))
    assert result.ok is True
    assert result.type == "test.echo"
    assert result.data == {"got": 7}
    assert result.error is None


def test_dispatch_unknown_type_returns_not_ok_without_raising():
    hub = Hub()
    result = hub.dispatch(HubEvent(type="test.missing", project_id="p1"))
    assert result.ok is False
    assert "no handler" in result.error


def test_dispatch_isolates_handler_failure():
    hub = Hub()

    def boom(_event):
        raise RuntimeError("specialist exploded")

    hub.register("test.boom", boom)
    # Must NOT raise - background failure is swallowed and reported structurally.
    result = hub.dispatch(HubEvent(type="test.boom", project_id="p1"))
    assert result.ok is False
    assert "specialist exploded" in result.error


def test_hub_result_has_no_user_facing_prose_field():
    """D8: dispatch results must carry only structured fields, no user prose.

    Guards against the Hub drifting into writing reminders / explanations.
    """
    field_names = {f.name for f in fields(HubResult)}
    forbidden = {"reply", "message", "text", "explanation", "prose", "content"}
    assert field_names.isdisjoint(forbidden)


# --------------------------------------------------------------- write gate


def test_get_event_log_returns_same_cached_instance(tmp_path):
    hub = Hub()
    events_dir = tmp_path / "events"
    a = hub.get_event_log(events_dir)
    b = hub.get_event_log(events_dir)
    assert a is b  # single cached instance per project -> shared _next_seq


def test_writer_appends_under_lock(tmp_path):
    hub = Hub()
    events_dir = tmp_path / "events"
    event_log = hub.get_event_log(events_dir)
    writer = hub.writer_for(event_log)
    seq, was_new = writer.append(
        event_id="evt_1",
        idempotency_key="k1",
        event_type="chat.message",
        payload={"role": "user", "content": "hi"},
    )
    assert was_new is True
    assert seq == 1
    events = list(event_log.read_events())
    assert len(events) == 1


def test_concurrent_writes_same_project_do_not_duplicate_seq(tmp_path):
    """Many threads writing the same project must produce unique, dense seqs."""
    hub = Hub()
    events_dir = tmp_path / "events"
    event_log = hub.get_event_log(events_dir)
    writer = hub.writer_for(event_log)

    n = 50
    barrier = threading.Barrier(n)

    def write(i):
        barrier.wait()  # maximize contention
        writer.append(
            event_id=f"evt_{i}",
            idempotency_key=f"k{i}",
            event_type="chat.message",
            payload={"i": i},
        )

    threads = [threading.Thread(target=write, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    seqs = sorted(e.seq for e in event_log.read_events())
    assert seqs == list(range(1, n + 1))  # unique + dense, no collisions


def test_different_projects_use_independent_locks(tmp_path):
    hub = Hub()
    log_a = hub.get_event_log(tmp_path / "a" / "events")
    log_b = hub.get_event_log(tmp_path / "b" / "events")
    assert log_a is not log_b
    # Holding project A's lock must not block writing to project B.
    with hub.project_lock(log_a):
        writer_b = hub.writer_for(log_b)
        seq, was_new = writer_b.append(
            event_id="evt_b1",
            idempotency_key="kb1",
            event_type="chat.message",
            payload={},
        )
        assert was_new is True


def test_project_lock_is_reentrant(tmp_path):
    """Code inside project_lock may also call writer.append (same RLock)."""
    hub = Hub()
    event_log = hub.get_event_log(tmp_path / "events")
    writer = hub.writer_for(event_log)
    with hub.project_lock(event_log):
        seq, was_new = writer.append(
            event_id="evt_1",
            idempotency_key="k1",
            event_type="manuscript.adopted",
            payload={},
        )
    assert was_new is True


def test_get_hub_returns_singleton():
    assert get_hub() is get_hub()


# ----------------------------------------------- existing write paths via Hub


def test_existing_write_paths_share_hub_cached_log(project_service, sample_project):
    """ProjectService.get_services must return the Hub-cached instance.

    This is what makes the per-project lock effective across DocumentService,
    extraction, contradiction, etc.
    """
    from app.services.hub import get_hub

    services = project_service.get_services(sample_project.id)
    event_log, _ = services
    project_dir = project_service.get_project_dir(sample_project.id)
    hub_log = get_hub().get_event_log(project_dir / "events")
    assert event_log is hub_log


def test_document_save_goes_through_hub_writer(project_service, sample_project):
    from app.services import DocumentService

    services = project_service.get_services(sample_project.id)
    event_log, _ = services
    doc = DocumentService(event_log)
    doc.save_revision("第一版正文")
    events = [
        e
        for e in event_log.read_events()
        if (e.type.value if hasattr(e.type, "value") else e.type) == "document.revised"
    ]
    assert len(events) == 1


# --------------------------------------------------------- architecture test


def test_no_direct_append_event_outside_event_log_and_hub():
    """D8 / Oracle MUST-FIX #5: append_event() must only be CALLED from the
    event log itself and the Hub append gateway. Any other direct call bypasses
    the per-project write lock and makes serialization a lie.
    """
    services_dir = Path(__file__).parent.parent / "app"
    allowed = {"event_log.py", "hub.py"}
    offenders: list[str] = []
    for path in services_dir.rglob("*.py"):
        if path.name in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        # Match an actual METHOD CALL ``.append_event(`` (e.g.
        # ``event_log.append_event(...)``). A bare ``append_event(`` would also
        # match the unrelated FastAPI route function named ``append_event``, so
        # we require the leading dot to target real calls only.
        if ".append_event(" in text:
            offenders.append(str(path.relative_to(services_dir)))
    assert offenders == [], (
        "These files call append_event() directly, bypassing the Hub write "
        f"lock: {offenders}"
    )
