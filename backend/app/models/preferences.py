"""ProjectPreference models for story state projection.

This aligns with the minimal-story-state spec.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectPreference(BaseModel):
    """A project-level preference that affects system judgment.

    Project preferences MUST be derived from accepted SystemEvent entries.
    They MUST NOT delete original facts, original continuity events,
    or original event log entries.
    """

    # Common fields
    source_event_id: str = Field(
        ..., description="Event that recorded the preference"
    )


class ConfirmedAssumptionPreference(ProjectPreference):
    """A confirmed project assumption or setting."""

    assumption: str = Field(..., description="The confirmed assumption or setting")
    confirmed_at: datetime = Field(..., description="When the assumption was confirmed")
    confirmed_by: str = Field(..., description="Actor that confirmed the assumption")
    related_continuity_event_id: Optional[str] = Field(
        None, description="Related continuity event, if any"
    )
    related_fact_ids: list[str] = Field(
        default_factory=list, description="Related facts"
    )


class DeweightingPreference(ProjectPreference):
    """A deweighting rule for a category of findings."""

    category: str = Field(
        ..., description="Finding category or matching rule being deweighted"
    )
    weight_delta: float = Field(
        ..., description="Priority effect (negative = lower priority)"
    )
    reason: str = Field(..., description="Why this deweighting was set")
    scope: str = Field(default="project", description="Scope of the deweighting")
