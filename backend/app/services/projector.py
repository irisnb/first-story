"""Projector Service - rebuilds story state from event log.

This service implements the projector-service spec:
- Rebuild state from event log
- Handle all event types
- Persist projection to file
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import (
    Character,
    CharacterStatus,
    ContinuityEvent,
    ContinuityEventStatus,
    Delivery,
    DocumentRevision,
    Fact,
    PlotEvent,
    Story,
    StoryState,
    StyleMemo,
    SystemEvent,
)
from .event_log import EventLogService


class ProjectorService:
    """Service for rebuilding story state from event log."""

    def __init__(self, event_log: EventLogService, project_dir: Path):
        """Initialize the projector service.

        Args:
            event_log: The event log service
            project_dir: Directory for the project (contains story_state.json)
        """
        self.event_log = event_log
        self.project_dir = project_dir
        self.state_file = project_dir / "story_state.json"

    def rebuild(self) -> StoryState:
        """Rebuild the story state from the event log.

        Returns:
            The rebuilt StoryState
        """
        # Initialize empty state
        story = Story()
        log_head_seq = 0
        head_event_id = None

        # Process all events in order
        for event in self.event_log.read_events():
            self._process_event(event, story)
            log_head_seq = event.seq
            head_event_id = event.event_id

        # Create state
        state = StoryState(
            projection_schema_version="1.0",
            log_head_seq=log_head_seq,
            head_event_id=head_event_id,
            story=story,
            updated_at=datetime.now(),
        )

        # Persist
        self._save_projection(state)

        return state

    def _process_event(self, event: SystemEvent, story: Story) -> None:
        """Process a single event and update the story state."""
        event_type = event.type.value if hasattr(event.type, "value") else event.type
        payload = event.payload

        handlers = {
            "character.created": lambda: self._process_character_created(event, story, payload),
            "character.status_updated": lambda: self._process_character_status_updated(event, story, payload),
            "plot_event.created": lambda: self._process_plot_event_created(event, story, payload),
            "fact.created": lambda: self._process_fact_created(event, story, payload),
            "document.revised": lambda: self._process_document_revised(event, story, payload),
            "continuity_event.created": lambda: self._process_continuity_event_created(event, story, payload),
            "continuity_event.ignored": lambda: self._process_continuity_event_ignored(event, story, payload),
            "continuity_event.resolved": lambda: self._process_continuity_event_resolved(event, story, payload),
            "project_preference.deweighting_set": lambda: self._process_project_preference_deweighting(event, story, payload),
            "project_preference.assumption_confirmed": lambda: self._process_project_preference_assumption(event, story, payload),
            "creative_intent.added": lambda: self._process_creative_intent_added(event, story, payload),
            "creative_intent.archived": lambda: self._process_creative_intent_archived(event, story, payload),
            "batch.committed": lambda: None,  # No state change
        }

        handler = handlers.get(event_type)
        if handler:
            handler()

    def _process_character_created(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process character.created event."""
        character = Character(
            id=payload.get("character_id"),
            name=payload.get("name", ""),
            status=CharacterStatus(payload.get("initial_status", "unknown")),
            status_since_event_id=event.event_id,
            status_note=payload.get("initial_status_note"),
            gender=payload.get("gender"),
            relations=[{"target_id": r.get("target_id"), "relation": r.get("relation")} for r in payload.get("relations", [])],
            known_fact_ids=[],
            attributes={},
        )
        story.characters.append(character)

    def _process_character_status_updated(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process character.status_updated event."""
        character_id = payload.get("character_id")
        for char in story.characters:
            if char.id == character_id:
                char.status = CharacterStatus(payload.get("new_status", "unknown"))
                char.status_since_event_id = event.event_id
                break

    def _process_plot_event_created(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process plot_event.created event."""
        plot_event = PlotEvent(
            id=payload.get("plot_event_id"),
            summary=payload.get("summary", ""),
            story_time=payload.get("story_time", {"type": "unknown"}),
            participant_character_ids=payload.get("participant_character_ids", []),
            asserted_fact_ids=payload.get("asserted_fact_ids", []),
            source_event_id=event.event_id,
        )
        story.plot_events.append(plot_event)

    def _process_fact_created(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process fact.created event."""
        fact = Fact(
            id=payload.get("fact_id"),
            content=payload.get("content", ""),
            story_time=payload.get("story_time"),
            about_character_ids=payload.get("about_character_ids", []),
            source_event_id=event.event_id,
            source_document_id=payload.get("source_document_id", ""),
            source_revision=payload.get("source_revision", ""),
            source_span=payload.get("source_span", {"start": 0, "end": 0}),
            source_text_hash=payload.get("source_text_hash", ""),
            source_plot_event_id=payload.get("source_plot_event_id"),
            extraction_confidence=payload.get("extraction_confidence", 0.5),
            # Historical defaults: facts written before these fields existed
            # came from editor prose, so they are committed+document.
            lifecycle_status=payload.get("lifecycle_status", "active"),
            acceptance_status=payload.get("acceptance_status", "committed"),
            source_type=payload.get("source_type", "document"),
        )
        story.facts.append(fact)

    def _process_document_revised(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process document.revised event - latest revision wins as projection."""
        story.current_document = DocumentRevision(
            revision_id=payload.get("revision_id", ""),
            document_id=payload.get("document_id", "main"),
            content=payload.get("content", ""),
            content_hash=payload.get("content_hash", ""),
            source_span=payload.get("source_span", {"start": 0, "end": 0}),
            revised_at=event.timestamp.isoformat()
            if hasattr(event.timestamp, "isoformat")
            else str(event.timestamp),
            source_event_id=event.event_id,
            restored_from_revision_id=payload.get("restored_from_revision_id"),
        )

    def _process_continuity_event_created(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process continuity_event.created event."""
        delivery_data = payload.get("delivery")
        delivery = None
        if delivery_data:
            delivery = Delivery(**delivery_data)

        continuity_event = ContinuityEvent(
            id=payload.get("continuity_event_id"),
            type=payload.get("type", ""),
            severity=payload.get("severity", "P3"),
            contradiction_confidence=payload.get("contradiction_confidence", 0.5),
            evidence_fact_ids=payload.get("evidence_fact_ids", []),
            affected_modules=payload.get("affected_modules", []),
            status=ContinuityEventStatus(payload.get("status", "queued")),
            source_event_id=event.event_id,
            title=payload.get("title"),
            involved_character_ids=payload.get("involved_character_ids", []),
            delivery=delivery,
        )
        story.continuity_events.append(continuity_event)

    def _process_continuity_event_ignored(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process continuity_event.ignored event."""
        continuity_event_id = payload.get("continuity_event_id")
        for ce in story.continuity_events:
            if ce.id == continuity_event_id:
                ce.status = ContinuityEventStatus.IGNORED
                ce.ignored_at = event.timestamp
                break

    def _process_continuity_event_resolved(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process continuity_event.resolved event."""
        continuity_event_id = payload.get("continuity_event_id")
        for ce in story.continuity_events:
            if ce.id == continuity_event_id:
                ce.status = ContinuityEventStatus.RESOLVED
                break

    def _process_project_preference_deweighting(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process project_preference.deweighting_set event."""
        from ..models.preferences import DeweightingPreference
        pref = DeweightingPreference(
            source_event_id=event.event_id,
            category=payload.get("category", ""),
            weight_delta=payload.get("weight_delta", 0.0),
            reason=payload.get("reason", ""),
            scope=payload.get("scope", "project"),
        )
        story.project_preferences.append(pref)

    def _process_project_preference_assumption(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process project_preference.assumption_confirmed event."""
        from ..models.preferences import ConfirmedAssumptionPreference
        pref = ConfirmedAssumptionPreference(
            source_event_id=event.event_id,
            assumption=payload.get("assumption", ""),
            confirmed_at=event.timestamp,
            confirmed_by=payload.get("confirmed_by", "user"),
            related_continuity_event_id=payload.get("related_continuity_event_id"),
            related_fact_ids=payload.get("related_fact_ids", []),
        )
        story.project_preferences.append(pref)

    def _process_creative_intent_added(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process creative_intent.added - append an active style memo."""
        memo = StyleMemo(
            id=payload.get("memo_id", event.event_id),
            text=payload.get("text", ""),
            kind=payload.get("kind") or "未分类",
            status="active",
            source_event_id=event.event_id,
        )
        story.style_memos.append(memo)

    def _process_creative_intent_archived(self, event: SystemEvent, story: Story, payload: dict) -> None:
        """Process creative_intent.archived - mark archived, never delete."""
        memo_id = payload.get("memo_id")
        for memo in story.style_memos:
            if memo.id == memo_id:
                memo.status = "archived"
                break

    def _save_projection(self, state: StoryState) -> None:
        """Persist the projection to file."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)

    def load_state(self) -> Optional[StoryState]:
        """Load the current projection from file.

        Returns:
            The StoryState if file exists, None otherwise
        """
        if not self.state_file.exists():
            return None

        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return StoryState(**data)
