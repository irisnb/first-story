"""Common types used across models.

These types align with the minimal-story-state spec.
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class StoryTimeAbsolute(BaseModel):
    """Absolute story time - a concrete timestamp or date."""

    type: Literal["absolute"] = "absolute"
    value: str = Field(..., description="Concrete time value (ISO date, timestamp, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of the time interpretation")


class StoryTimeRelative(BaseModel):
    """Relative story time - relation to an anchor point."""

    type: Literal["relative"] = "relative"
    anchor: str = Field(..., description="Anchor point (e.g., 'story_start', 'story_now', or an event ID)")
    direction: Literal["before", "after", "same"] = Field(
        ..., description="Direction relative to anchor"
    )
    distance: Optional[str] = Field(None, description="Distance from anchor (e.g., '10年', '1天')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of the time interpretation")


class StoryTimeUnknown(BaseModel):
    """Unknown or unavailable story time."""

    type: Literal["unknown"] = "unknown"


StoryTime = StoryTimeAbsolute | StoryTimeRelative | StoryTimeUnknown


class SourceSpan(BaseModel):
    """Source text range within a document."""

    start: int = Field(..., ge=0, description="Start position (0-indexed)")
    end: int = Field(..., ge=0, description="End position (exclusive)")


class CharacterStatus(str, Enum):
    """Machine-readable character status."""

    ALIVE = "alive"
    DEAD = "dead"
    UNKNOWN = "unknown"


class ContinuityEventStatus(str, Enum):
    """Lifecycle status of a continuity event."""

    NEW = "new"
    QUEUED = "queued"
    SHOWN = "shown"
    IGNORED = "ignored"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class FactLifecycleStatus(str, Enum):
    """Lifecycle status of a fact.

    Whether the assertion is still in force. Orthogonal to acceptance_status.
    """

    ACTIVE = "active"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


class FactAcceptanceStatus(str, Enum):
    """Acceptance status of a fact - how trustworthy its source is.

    Orthogonal to ``FactLifecycleStatus``: a fact can be active+committed or
    active+candidate. NEVER reuse lifecycle to express this.

    - ``committed``: a formal setting, from editor prose or adopted chat.
    - ``candidate``: a brainstorm/hypothesis from chat; never enters
      contradiction detection.

    Historical facts (written before this field existed) default to
    ``committed`` on read - they all came from editor prose.
    """

    COMMITTED = "committed"
    CANDIDATE = "candidate"


class FactSourceType(str, Enum):
    """Where the prose a fact was extracted from originated.

    Historical facts default to ``document`` on read.
    """

    DOCUMENT = "document"
    CHAT = "chat"


class Severity(str, Enum):
    """Priority/severity levels for continuity events."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"


class DeliveryMode(str, Enum):
    """How a continuity event should be delivered."""

    QUEUED_REMINDER = "queued_reminder"
    CARD_ONLY = "card_only"
    SILENT_RECORD = "silent_record"
    REPORT = "report"


class ArmorLevel(str, Enum):
    """Expression thickness for delivery."""

    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class Relation(BaseModel):
    """A relationship between characters."""

    target_id: str = Field(..., description="ID of the related character")
    relation: str = Field(..., description="Relationship type (e.g., '亲人', '朋友')")
