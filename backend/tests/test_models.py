"""Tests for data models."""

import sys
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import (
    Character,
    CharacterStatus,
    ContinuityEvent,
    ContinuityEventStatus,
    Fact,
    PlotEvent,
    Project,
    Severity,
    StoryState,
)


class TestCharacter:
    """Tests for Character model."""

    def test_character_creation(self):
        """Test basic character creation."""
        char = Character(
            id="char_001",
            name="Alice",
            status=CharacterStatus.ALIVE,
        )
        assert char.id == "char_001"
        assert char.name == "Alice"
        assert char.status == CharacterStatus.ALIVE
        assert char.known_fact_ids == []
        assert char.attributes == {}

    def test_character_with_relations(self):
        """Test character with relations."""
        char = Character(
            id="char_001",
            name="Alice",
            status=CharacterStatus.ALIVE,
            relations=[{"target_id": "char_002", "relation": "姐妹"}],
        )
        assert len(char.relations) == 1
        assert char.relations[0].target_id == "char_002"


class TestPlotEvent:
    """Tests for PlotEvent model."""

    def test_plot_event_creation(self):
        """Test basic plot event creation."""
        event = PlotEvent(
            id="plot_001",
            summary="Alice meets Bob",
            story_time={"type": "unknown"},
            source_event_id="evt_001",
        )
        assert event.id == "plot_001"
        assert event.summary == "Alice meets Bob"
        assert event.participant_character_ids == []


class TestFact:
    """Tests for Fact model."""

    def test_fact_creation(self):
        """Test basic fact creation."""
        fact = Fact(
            id="fact_001",
            content="Alice is 25 years old",
            source_event_id="evt_001",
            source_document_id="script_current",
            source_revision="rev_001",
            source_span={"start": 0, "end": 20},
            source_text_hash="abc123",
            extraction_confidence=0.9,
        )
        assert fact.id == "fact_001"
        assert fact.content == "Alice is 25 years old"
        assert fact.extraction_confidence == 0.9


class TestContinuityEvent:
    """Tests for ContinuityEvent model."""

    def test_continuity_event_creation(self):
        """Test basic continuity event creation."""
        event = ContinuityEvent(
            id="cont_001",
            type="character_status_conflict",
            severity=Severity.P2,
            contradiction_confidence=0.82,
            evidence_fact_ids=["fact_001", "fact_002"],
            source_event_id="evt_001",
        )
        assert event.id == "cont_001"
        assert event.severity == Severity.P2
        assert event.status == ContinuityEventStatus.QUEUED


class TestStoryState:
    """Tests for StoryState model."""

    def test_empty_state(self):
        """Test empty state creation."""
        state = StoryState()
        assert state.log_head_seq == 0
        assert state.head_event_id is None
        assert state.story.characters == []
        assert state.story.facts == []

    def test_state_with_characters(self):
        """Test state with characters."""
        char = Character(id="char_001", name="Alice")
        state = StoryState(story={"characters": [char]})
        assert len(state.story.characters) == 1


class TestProject:
    """Tests for Project model."""

    def test_project_creation(self):
        """Test project creation."""
        from datetime import datetime

        now = datetime.now()
        project = Project(
            id="proj_001",
            name="My Story",
            created_at=now,
            updated_at=now,
        )
        assert project.id == "proj_001"
        assert project.name == "My Story"
        assert project.version == "1.0.0"
