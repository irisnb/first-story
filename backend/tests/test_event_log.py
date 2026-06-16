"""Tests for EventLogService."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import EventLogService


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
