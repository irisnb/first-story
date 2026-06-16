"""Tests for ProjectorService."""

import sys
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))



class TestProjectorService:
    """Tests for ProjectorService."""

    def test_rebuild_empty_log(self, projector_service):
        """Test rebuilding from an empty log."""
        state = projector_service.rebuild()
        assert state.log_head_seq == 0
        assert state.head_event_id is None
        assert len(state.story.characters) == 0

    def test_rebuild_with_character(self, event_log_service, projector_service):
        """Test rebuilding with character events."""
        event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="char_001",
            event_type="character.created",
            payload={
                "character_id": "char_001",
                "name": "Alice",
                "initial_status": "alive",
            },
        )

        state = projector_service.rebuild()
        assert len(state.story.characters) == 1
        assert state.story.characters[0].name == "Alice"
        assert state.story.characters[0].status.value == "alive"

    def test_rebuild_with_character_status_update(
        self, event_log_service, projector_service
    ):
        """Test rebuilding with character status update."""
        # Create character
        event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="char_001",
            event_type="character.created",
            payload={
                "character_id": "char_001",
                "name": "Alice",
                "initial_status": "alive",
            },
        )

        # Update status
        event_log_service.append_event(
            event_id="evt_002",
            idempotency_key="char_001_status",
            event_type="character.status_updated",
            payload={
                "character_id": "char_001",
                "previous_status": "alive",
                "new_status": "dead",
            },
        )

        state = projector_service.rebuild()
        assert state.story.characters[0].status.value == "dead"
        assert state.log_head_seq == 2

    def test_rebuild_with_fact(self, event_log_service, projector_service):
        """Test rebuilding with fact events."""
        event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="fact_001",
            event_type="fact.created",
            payload={
                "fact_id": "fact_001",
                "content": "Alice is 25 years old",
                "source_document_id": "script_current",
                "source_revision": "rev_001",
                "source_span": {"start": 0, "end": 20},
                "source_text_hash": "abc123",
                "extraction_confidence": 0.9,
            },
        )

        state = projector_service.rebuild()
        assert len(state.story.facts) == 1
        assert state.story.facts[0].content == "Alice is 25 years old"

    def test_rebuild_with_plot_event(self, event_log_service, projector_service):
        """Test rebuilding with plot event."""
        event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="plot_001",
            event_type="plot_event.created",
            payload={
                "plot_event_id": "plot_001",
                "summary": "Alice meets Bob",
                "story_time": {"type": "unknown"},
                "participant_character_ids": ["char_001"],
            },
        )

        state = projector_service.rebuild()
        assert len(state.story.plot_events) == 1
        assert state.story.plot_events[0].summary == "Alice meets Bob"

    def test_rebuild_with_continuity_event(
        self, event_log_service, projector_service
    ):
        """Test rebuilding with continuity events."""
        # Create continuity event
        event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="cont_001",
            event_type="continuity_event.created",
            payload={
                "continuity_event_id": "cont_001",
                "type": "character_status_conflict",
                "severity": "P2",
                "contradiction_confidence": 0.82,
                "evidence_fact_ids": ["fact_001", "fact_002"],
                "status": "queued",
            },
        )

        state = projector_service.rebuild()
        assert len(state.story.continuity_events) == 1
        assert state.story.continuity_events[0].type == "character_status_conflict"

    def test_rebuild_with_continuity_ignored(
        self, event_log_service, projector_service
    ):
        """Test rebuilding with ignored continuity event."""
        # Create continuity event
        event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="cont_001",
            event_type="continuity_event.created",
            payload={
                "continuity_event_id": "cont_001",
                "type": "character_status_conflict",
                "severity": "P2",
                "contradiction_confidence": 0.82,
                "evidence_fact_ids": [],
                "status": "queued",
            },
        )

        # Ignore it
        event_log_service.append_event(
            event_id="evt_002",
            idempotency_key="cont_001_ignore",
            event_type="continuity_event.ignored",
            payload={
                "continuity_event_id": "cont_001",
                "scope": "single_finding",
            },
        )

        state = projector_service.rebuild()
        assert state.story.continuity_events[0].status.value == "ignored"
        assert state.story.continuity_events[0].ignored_at is not None

    def test_load_state(self, event_log_service, projector_service):
        """Test loading state from file."""
        # Create some events
        event_log_service.append_event(
            event_id="evt_001",
            idempotency_key="char_001",
            event_type="character.created",
            payload={
                "character_id": "char_001",
                "name": "Alice",
                "initial_status": "alive",
            },
        )

        # Rebuild
        state1 = projector_service.rebuild()

        # Load from file
        state2 = projector_service.load_state()
        assert state2 is not None
        assert state2.log_head_seq == state1.log_head_seq
        assert len(state2.story.characters) == 1
