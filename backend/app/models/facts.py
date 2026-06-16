"""Fact model for story state projection.

This aligns with the minimal-story-state spec.
"""

from typing import Optional

from pydantic import BaseModel, Field

from .common import FactLifecycleStatus, SourceSpan, StoryTime


class Fact(BaseModel):
    """A minimal story assertion that can be cited as evidence.

    Facts trace back to their source event and original document span.
    """

    id: str = Field(..., description="Stable identifier")
    content: str = Field(..., description="Human-readable assertion text")
    story_time: Optional[StoryTime] = Field(
        None, description="When this fact occurred in the story"
    )
    about_character_ids: list[str] = Field(
        default_factory=list, description="Related characters"
    )
    source_event_id: str = Field(
        ..., description="SystemEvent.event_id that introduced the fact"
    )
    source_document_id: str = Field(
        ..., description="Script document that contains the source prose"
    )
    source_revision: str = Field(
        ..., description="Script document revision observed during extraction"
    )
    source_span: SourceSpan = Field(
        ..., description="Source text range within the script document"
    )
    source_text_hash: str = Field(
        ..., description="Hash of the source text used to extract the fact"
    )
    source_plot_event_id: Optional[str] = Field(
        None, description="PlotEvent.id when the fact comes from a story-world event"
    )
    extraction_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence that the system correctly extracted this"
    )
    lifecycle_status: FactLifecycleStatus = Field(
        default=FactLifecycleStatus.ACTIVE,
        description="Lifecycle state",
    )
