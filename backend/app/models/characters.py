"""Character model for story state projection.

This aligns with the minimal-story-state spec.
"""

from typing import Optional

from pydantic import BaseModel, Field

from .common import CharacterStatus, Relation


class Character(BaseModel):
    """A character in the story.

    Deterministic contradiction checks MUST use `status` and MUST NOT
    parse `status_note` as authoritative machine state.
    """

    id: str = Field(..., description="Stable identifier")
    name: str = Field(..., description="Display name")
    status: CharacterStatus = Field(
        default=CharacterStatus.UNKNOWN,
        description="Machine-readable current status",
    )
    status_since_event_id: Optional[str] = Field(
        None, description="SystemEvent.event_id from which the current status became effective"
    )
    status_note: Optional[str] = Field(
        None, description="Optional human-readable note (not used for deterministic checks)"
    )
    gender: Optional[str] = Field(None, description="Character gender")
    relations: list[Relation] = Field(
        default_factory=list, description="Relationship records to other characters"
    )
    known_fact_ids: list[str] = Field(
        default_factory=list, description="Facts known to this character, when tracked"
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Dynamic attributes accumulated from facts",
    )
