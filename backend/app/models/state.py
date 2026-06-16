"""StoryState and Story projection models.

This aligns with the minimal-story-state spec.
"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field

from .characters import Character
from .continuity import ContinuityEvent
from .facts import Fact
from .plot_events import PlotEvent
from .preferences import ConfirmedAssumptionPreference, DeweightingPreference


class StoryClock(BaseModel):
    """Structured story timeline state."""

    current_time: Optional[str] = Field(
        None, description="Current time in the story"
    )
    reference_point: str = Field(
        default="story_start", description="Reference point for time calculations"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence of the time state"
    )


class Story(BaseModel):
    """The story state content."""

    story_clock: Optional[StoryClock] = Field(
        None, description="Structured story timeline state"
    )
    characters: list[Character] = Field(
        default_factory=list, description="Character objects"
    )
    plot_events: list[PlotEvent] = Field(
        default_factory=list, description="PlotEvent objects"
    )
    facts: list[Fact] = Field(
        default_factory=list, description="Fact objects"
    )
    continuity_events: list[ContinuityEvent] = Field(
        default_factory=list, description="ContinuityEvent objects"
    )
    project_preferences: list[Union[ConfirmedAssumptionPreference, DeweightingPreference]] = Field(
        default_factory=list,
        description="Project-level preferences, deweighting rules, and confirmed assumptions",
    )


class StoryState(BaseModel):
    """The current story state projection.

    This is a rebuildable projection from the event log, NOT the source of truth.
    The event log is the source of truth for AI-structured story state.
    """

    projection_schema_version: str = Field(
        default="1.0", description="Schema version for projection structure"
    )
    log_head_seq: int = Field(
        default=0, description="Highest seq processed from event log"
    )
    head_event_id: Optional[str] = Field(
        None, description="event_id of the highest seq event"
    )
    source_document_revision: Optional[str] = Field(
        None, description="Document revision if tracked"
    )
    source_document_checksum: Optional[str] = Field(
        None, description="Document checksum if tracked"
    )
    story: Story = Field(
        default_factory=Story, description="The story state content"
    )
    updated_at: Optional[datetime] = Field(
        None, description="When this projection was last updated"
    )
