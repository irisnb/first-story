"""Tests for context summary trigger functionality."""

import pytest

from app.services.dialogue import DialogueAgent, DialogueResult
from app.services.event_log import EventLogService
from app.services.projector import ProjectorService
from app.models.events import EventType


def test_dialogue_result_has_turn_count():
    """DialogueResult should have turn_count field with default 0."""
    result = DialogueResult(
        reply="test",
        message_id="msg_1",
        intent="ignore",
        extraction_status="none",
        user_message_id="msg_0",
        llm_succeeded=True,
    )
    assert result.turn_count == 0


def test_dialogue_result_turn_count_can_be_set():
    """DialogueResult turn_count can be set."""
    result = DialogueResult(
        reply="test",
        message_id="msg_1",
        intent="ignore",
        extraction_status="none",
        user_message_id="msg_0",
        llm_succeeded=True,
        turn_count=10,
    )
    assert result.turn_count == 10


def test_turn_count_increments_on_user_message(tmp_path):
    """Turn count should increment after each user message."""
    events_dir = tmp_path / "events"
    events_dir.mkdir()

    event_log = EventLogService(events_dir)
    projector = ProjectorService(event_log, tmp_path)
    agent = DialogueAgent(event_log, projector=projector)

    # First message
    result1 = agent.respond("Hello")
    assert result1.turn_count == 1

    # Second message
    result2 = agent.respond("World")
    assert result2.turn_count == 2

    # Third message
    result3 = agent.respond("Test")
    assert result3.turn_count == 3


def test_turn_count_persisted_in_event(tmp_path):
    """Turn count should be written to context_summary.updated event."""
    events_dir = tmp_path / "events"
    events_dir.mkdir()

    event_log = EventLogService(events_dir)
    projector = ProjectorService(event_log, tmp_path)
    agent = DialogueAgent(event_log, projector=projector)

    agent.respond("First message")

    # Check that context_summary.updated event was written
    events = list(event_log.read_events())
    summary_events = [e for e in events if e.type == EventType.CONTEXT_SUMMARY_UPDATED]
    assert len(summary_events) == 1
    assert summary_events[0].payload.get("turn_count") == 1


def test_turn_count_loaded_from_state(tmp_path):
    """Turn count should be loaded from existing state."""
    events_dir = tmp_path / "events"
    events_dir.mkdir()

    event_log = EventLogService(events_dir)
    projector = ProjectorService(event_log, tmp_path)

    # First session: send 5 messages
    agent1 = DialogueAgent(event_log, projector=projector)
    for i in range(5):
        agent1.respond(f"Message {i}")

    # Rebuild projection
    projector.rebuild()

    # Second session: create new agent, should resume from turn 5
    agent2 = DialogueAgent(event_log, projector=projector)
    result = agent2.respond("New session message")
    assert result.turn_count == 6


def test_context_summary_updated_event_has_correct_fields(tmp_path):
    """context_summary.updated event should have correct structure."""
    events_dir = tmp_path / "events"
    events_dir.mkdir()

    event_log = EventLogService(events_dir)
    projector = ProjectorService(event_log, tmp_path)
    agent = DialogueAgent(event_log, projector=projector)

    agent.respond("Test message")

    events = list(event_log.read_events())
    summary_events = [e for e in events if e.type == EventType.CONTEXT_SUMMARY_UPDATED]
    assert len(summary_events) == 1

    event = summary_events[0]
    assert "turn_count" in event.payload
    assert event.payload["turn_count"] == 1


def test_projector_handles_turn_count_event(tmp_path):
    """Projector should correctly update context_summary.turn_count."""
    events_dir = tmp_path / "events"
    events_dir.mkdir()

    event_log = EventLogService(events_dir)
    projector = ProjectorService(event_log, tmp_path)

    # Write events directly
    from app.services.hub import get_hub
    hub = get_hub()
    writer = hub.writer_for(event_log)

    # Write a context_summary.updated event with turn_count
    writer.append(
        event_id="evt_001",
        idempotency_key="test_turn_count_1",
        event_type="context_summary.updated",
        payload={"turn_count": 42},
        actor="hub",  # Use valid actor value
    )

    # Rebuild and check
    state = projector.rebuild()
    assert state.story.context_summary.turn_count == 42
