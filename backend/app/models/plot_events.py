"""PlotEvent model for story state projection.

This aligns with the minimal-story-state spec.
"""


from pydantic import BaseModel, Field

from .common import StoryTime


class PlotEvent(BaseModel):
    """An event inside the story world.

    This is NOT an event log entry - it's a story-world event.
    """

    id: str = Field(..., description="Stable identifier")
    summary: str = Field(..., description="Human-readable summary")
    story_time: StoryTime = Field(
        ..., description="Structured story time value (absolute, relative, or unknown)"
    )
    participant_character_ids: list[str] = Field(
        default_factory=list, description="Involved characters (IDs)"
    )
    participant_character_names: list[str] = Field(
        default_factory=list, description="Involved characters (names)"
    )
    asserted_fact_ids: list[str] = Field(
        default_factory=list, description="Facts asserted by this plot event"
    )
    source_event_id: str = Field(
        ..., description="SystemEvent.event_id that introduced or updated this plot event"
    )
    acceptance_status: str = Field(
        default="committed",
        description="Whether this plot event is candidate or committed",
    )
