"""Tests for EventLogService."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))



class TestEventLogService:
    """Tests for EventLogService."""

    def test_init_creates_log_file(self, event_log_service, sample_project):
        """Test that initialization creates the log file."""
        project_dir = event_log_service.events_dir.parent
        log_file = project_dir / "events" / "00001.jsonl"
        assert log_file.exists()

    def test_append_event(self, event_log_service):
        """Test appending a single event."""
        seq, was_new = event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="test_key_1",
            event_type="character.created",
            payload={"character_id": "char_001", "name": "Alice"},
        )
        assert seq == 1
        assert was_new is True
        assert event_log_service.get_event_count() == 1

    def test_append_multiple_events(self, event_log_service):
        """Test appending multiple events."""
        for i in range(5):
            event_log_service.append_event(
                event_id=f"evt_{i:03d}",
                idempotency_key=f"test_key_{i}",
                event_type="fact.created",
                payload={"fact_id": f"fact_{i}"},
            )
        assert event_log_service.get_event_count() == 5
        assert event_log_service.get_max_seq() == 5

    def test_idempotency_check(self, event_log_service):
        """Test that duplicate events are rejected."""
        # First append
        seq1, was_new1 = event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="duplicate_key",
            event_type="character.created",
            payload={"character_id": "char_001"},
        )
        assert seq1 == 1
        assert was_new1 is True

        # Second append with same idempotency_key
        seq2, was_new2 = event_log_service.append_event(
            event_id="evt_002",  # Different event_id
            idempotency_key="duplicate_key",  # Same key
            event_type="character.created",
            payload={"character_id": "char_001"},
        )
        assert seq2 == 1  # Returns same seq
        assert was_new2 is False  # Not new
        assert event_log_service.get_event_count() == 1  # Still 1 event

    def test_read_events(self, event_log_service):
        """Test reading events."""
        # Append events
        for i in range(3):
            event_log_service.append_event(
                event_id=f"evt_{i:03d}",
                idempotency_key=f"key_{i}",
                event_type="fact.created",
                payload={"index": i},
            )

        # Read all
        events = list(event_log_service.read_events())
        assert len(events) == 3
        assert events[0].seq == 1
        assert events[1].seq == 2
        assert events[2].seq == 3

    def test_read_events_from_seq(self, event_log_service):
        """Test reading events from a specific seq."""
        for i in range(5):
            event_log_service.append_event(
                event_id=f"evt_{i:03d}",
                idempotency_key=f"key_{i}",
                event_type="fact.created",
                payload={"index": i},
            )

        # Read from seq 3
        events = list(event_log_service.read_events(from_seq=3))
        assert len(events) == 3
        assert events[0].seq == 3

    def test_batch_events(self, event_log_service):
        """Test batch events with batch_id."""
        batch_id = "batch_001"
        for i in range(3):
            event_log_service.append_event(
                event_id=f"evt_{i:03d}",
                idempotency_key=f"key_{i}",
                event_type="fact.created",
                payload={"index": i},
                batch_id=batch_id,
            )

        # Get events by batch
        events = event_log_service.get_events_by_batch(batch_id)
        assert len(events) == 3


class TestReplayFailFast:
    """Tests for replay fail-fast behavior (P0 security fix)."""

    def test_malformed_jsonl_raises_error(self, event_log_service):
        """Test that malformed JSONL raises an error instead of silently skipping."""
        # Write malformed JSON directly to the log file
        log_file = event_log_service.log_file
        with open(log_file, "w", encoding="utf-8") as f:
            f.write('{"seq": 1, "type": "character.created", "payload": {}}\n')
            f.write("THIS IS NOT VALID JSON\n")  # Malformed line
            f.write('{"seq": 2, "type": "fact.created", "payload": {}}\n')

        # Reading events should raise an error, not silently skip the bad line
        with pytest.raises(Exception):
            list(event_log_service.read_events())

    def test_unknown_event_type_raises_error(self, event_log_service):
        """Test that unknown event types raise an error during replay."""
        # Write event with unknown type directly to the log file
        log_file = event_log_service.log_file
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(
                '{"event_id": "evt_001", "idempotency_key": "key_1", "seq": 1, '
                '"timestamp": "2026-01-01T00:00:00", "type": "unknown.event_type", '
                '"schema_version": "1.0", "payload": {}, "base_state_version": 0, "actor": "user"}\n'
            )

        # Reading events should raise an error for unknown event type
        with pytest.raises(Exception):
            list(event_log_service.read_events())

    def test_missing_required_field_raises_error(self, event_log_service):
        """Test that missing required fields raise an error during replay."""
        # Write event missing required 'seq' field
        log_file = event_log_service.log_file
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(
                '{"event_id": "evt_001", "idempotency_key": "key_1", '
                '"timestamp": "2026-01-01T00:00:00", "type": "character.created", '
                '"schema_version": "1.0", "payload": {}, "base_state_version": 0, "actor": "user"}\n'
            )

        # Reading events should raise an error for missing required field
        with pytest.raises(Exception):
            list(event_log_service.read_events())


class TestNewEventTypesReplay:
    """Replay must accept the dialogue/intent/adopt event types (group 1.2)."""

    def test_replay_new_event_types_does_not_crash(self, event_log_service):
        """chat.message / creative_intent.* / manuscript.adopted replay cleanly."""
        new_types = [
            "chat.message",
            "creative_intent.added",
            "creative_intent.archived",
            "manuscript.adopted",
        ]
        for i, event_type in enumerate(new_types, start=1):
            seq, was_new = event_log_service.append_event(
                event_id=f"evt_{i:03d}",
                idempotency_key=f"new_key_{i}",
                event_type=event_type,
                payload={"index": i},
            )
            assert was_new is True

        events = list(event_log_service.read_events())
        assert len(events) == len(new_types)
        assert [e.type.value for e in events] == new_types
