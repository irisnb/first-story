"""ContinuityEvent and Delivery models for story state projection.

This aligns with the minimal-story-state spec.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .common import ArmorLevel, ContinuityEventStatus, DeliveryMode, Severity


class Delivery(BaseModel):
    """Delivery metadata for a continuity event."""

    delivery_mode: DeliveryMode = Field(
        ..., description="How the event should be delivered"
    )
    interrupt_risk: str = Field(
        "medium", description="Estimated risk of interrupting user flow"
    )
    armor_level: ArmorLevel = Field(
        ArmorLevel.LIGHT, description="Expression thickness selected by Timing Policy"
    )
    initiator: str = Field(
        "system", description="Whether the system or user initiated the surface"
    )
    flow_blocked: bool = Field(
        False, description="Whether flow mode blocks active interruption"
    )


class ContinuityEvent(BaseModel):
    """A system-discovered continuity finding.

    This is NOT a final creative judgment - it's evidence for the user to consider.

    Background Agents MUST store evidence and finding metadata only.
    They MUST NOT store possible creative explanations (e.g., "ghost story", "fake death")
    as authoritative finding data.
    """

    id: str = Field(..., description="Stable identifier")
    type: str = Field(
        ..., description="Machine-readable finding type (e.g., 'character_status_conflict')"
    )
    severity: Severity = Field(..., description="P1-P5 delivery priority/severity")
    contradiction_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence that the cited facts form a conflict"
    )
    evidence_fact_ids: list[str] = Field(
        ..., description="Cited Fact.id values"
    )
    affected_modules: list[str] = Field(
        default_factory=list, description="Impacted modules such as character or plot"
    )
    status: ContinuityEventStatus = Field(
        ContinuityEventStatus.QUEUED, description="Lifecycle status"
    )
    source_event_id: str = Field(
        ..., description="SystemEvent.event_id that recorded the finding"
    )
    title: Optional[str] = Field(
        None, description="Human-readable one-line summary"
    )
    involved_character_ids: list[str] = Field(
        default_factory=list, description="Characters involved in this finding"
    )
    ignored_at: Optional[datetime] = Field(
        None, description="Timestamp when user ignored this finding"
    )
    ignored_days: int = Field(
        default=0, description="Number of days since ignored (for priority escalation)"
    )
    delivery: Optional[Delivery] = Field(
        None, description="Delivery metadata or pointer to delivery queue entry"
    )
