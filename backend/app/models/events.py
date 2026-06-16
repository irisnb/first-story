"""SystemEvent and event type definitions.

These align with the event-log spec.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Actor(str, Enum):
    """Origin of an event."""

    USER = "user"
    HUB = "hub"
    EXTRACTION_AGENT = "extraction_agent"
    CONTINUITY_AGENT = "continuity_agent"
    DIALOGUE_GATEWAY = "dialogue_gateway"


class EventType(str, Enum):
    """Types of system events."""

    # Character events
    CHARACTER_CREATED = "character.created"
    CHARACTER_STATUS_UPDATED = "character.status_updated"

    # Plot events
    PLOT_EVENT_CREATED = "plot_event.created"

    # Fact events
    FACT_CREATED = "fact.created"
    FACT_RETRACTED = "fact.retracted"

    # Continuity events
    CONTINUITY_EVENT_CREATED = "continuity_event.created"
    CONTINUITY_EVENT_IGNORED = "continuity_event.ignored"
    CONTINUITY_EVENT_RESOLVED = "continuity_event.resolved"

    # Project preferences
    PROJECT_PREFERENCE_DEWEIGHTING_SET = "project_preference.deweighting_set"
    PROJECT_PREFERENCE_ASSUMPTION_CONFIRMED = "project_preference.assumption_confirmed"

    # Batch events
    BATCH_COMMITTED = "batch.committed"


class SystemEvent(BaseModel):
    """A system event in the append-only log.

    This is the core data structure for the event log.
    """

    event_id: str = Field(..., description="Globally unique event identity (UUIDv7 or ULID)")
    idempotency_key: str = Field(
        ..., description="Stable deduplication key for retry-safe acceptance"
    )
    seq: int = Field(..., ge=1, description="Monotonically increasing log sequence")
    timestamp: datetime = Field(..., description="Wall-clock write time in ISO 8601 format")
    type: EventType = Field(..., description="Machine-readable mutation type")
    schema_version: str = Field(default="1.0", description="Schema version for event payload")
    payload: dict[str, Any] = Field(..., description="Mutation-specific structured data")
    base_state_version: int = Field(
        ..., ge=0, description="State version observed when the event was proposed"
    )
    actor: Actor = Field(..., description="Origin of the event")
    batch_id: Optional[str] = Field(None, description="Batch identifier for multi-event operations")


# Payload types for type-safe event creation


class CharacterCreatedPayload(BaseModel):
    """Payload for character.created event."""

    character_id: str
    name: str
    gender: Optional[str] = None
    initial_status: str = "unknown"
    initial_status_note: Optional[str] = None
    relations: list[dict] = Field(default_factory=list)


class CharacterStatusUpdatedPayload(BaseModel):
    """Payload for character.status_updated event."""

    character_id: str
    previous_status: str
    new_status: str
    reason_fact_id: Optional[str] = None


class PlotEventCreatedPayload(BaseModel):
    """Payload for plot_event.created event."""

    plot_event_id: str
    summary: str
    story_time: dict
    participant_character_ids: list[str] = Field(default_factory=list)
    asserted_fact_ids: list[str] = Field(default_factory=list)


class FactCreatedPayload(BaseModel):
    """Payload for fact.created event."""

    fact_id: str
    content: str
    story_time: Optional[dict] = None
    about_character_ids: list[str] = Field(default_factory=list)
    source_document_id: str
    source_revision: str
    source_span: dict
    source_text_hash: str
    source_plot_event_id: Optional[str] = None
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    lifecycle_status: str = "active"


class ContinuityEventCreatedPayload(BaseModel):
    """Payload for continuity_event.created event."""

    continuity_event_id: str
    type: str
    severity: str
    contradiction_confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_fact_ids: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    status: str = "queued"
    title: Optional[str] = None
    involved_character_ids: list[str] = Field(default_factory=list)
    delivery: Optional[dict] = None


class ContinuityEventIgnoredPayload(BaseModel):
    """Payload for continuity_event.ignored event."""

    continuity_event_id: str
    user_explanation: Optional[str] = None
    scope: str = "single_finding"


class ContinuityEventResolvedPayload(BaseModel):
    """Payload for continuity_event.resolved event."""

    continuity_event_id: str
    resolution_fact_id: Optional[str] = None


class DeweightingSetPayload(BaseModel):
    """Payload for project_preference.deweighting_set event."""

    category: str
    weight_delta: float
    reason: str
    scope: str = "project"


class AssumptionConfirmedPayload(BaseModel):
    """Payload for project_preference.assumption_confirmed event."""

    assumption: str
    confirmed_by: str
    related_continuity_event_id: Optional[str] = None
    related_fact_ids: list[str] = Field(default_factory=list)


class BatchCommittedPayload(BaseModel):
    """Payload for batch.committed event."""

    member_event_ids: list[str] = Field(default_factory=list)
    source_document_id: Optional[str] = None
    source_revision: Optional[str] = None
