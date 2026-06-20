"""Data models for the First Story backend."""

from .api import (
    AppendEventRequest,
    CreateProjectRequest,
    ErrorResponse,
    EventListResponse,
    EventResponse,
    HealthResponse,
    ProjectListResponse,
    ProjectResponse,
    RebuildResponse,
    StateResponse,
)
from .characters import Character
from .common import (
    ArmorLevel,
    CharacterStatus,
    ContinuityEventStatus,
    DeliveryMode,
    FactAcceptanceStatus,
    FactLifecycleStatus,
    FactSourceType,
    Relation,
    Severity,
    SourceSpan,
    StoryTime,
    StoryTimeAbsolute,
    StoryTimeRelative,
    StoryTimeUnknown,
)
from .continuity import ContinuityEvent, Delivery
from .documents import DocumentRevision, compute_text_hash
from .events import (
    Actor,
    AssumptionConfirmedPayload,
    BatchCommittedPayload,
    CharacterCreatedPayload,
    CharacterStatusUpdatedPayload,
    ContinuityEventCreatedPayload,
    ContinuityEventIgnoredPayload,
    ContinuityEventResolvedPayload,
    DeweightingSetPayload,
    DocumentRevisedPayload,
    EventType,
    FactCreatedPayload,
    PlotEventCreatedPayload,
    SystemEvent,
)
from .facts import Fact
from .plot_events import PlotEvent
from .preferences import ConfirmedAssumptionPreference, DeweightingPreference, ProjectPreference
from .project import Project
from .state import Story, StoryClock, StoryState, StyleMemo

__all__ = [
    # Common types
    "StoryTime",
    "StoryTimeAbsolute",
    "StoryTimeRelative",
    "StoryTimeUnknown",
    "SourceSpan",
    "CharacterStatus",
    "ContinuityEventStatus",
    "FactLifecycleStatus",
    "FactAcceptanceStatus",
    "FactSourceType",
    "Severity",
    "DeliveryMode",
    "ArmorLevel",
    "Relation",
    # Events
    "SystemEvent",
    "EventType",
    "Actor",
    "CharacterCreatedPayload",
    "CharacterStatusUpdatedPayload",
    "PlotEventCreatedPayload",
    "FactCreatedPayload",
    "ContinuityEventCreatedPayload",
    "ContinuityEventIgnoredPayload",
    "ContinuityEventResolvedPayload",
    "DeweightingSetPayload",
    "AssumptionConfirmedPayload",
    "BatchCommittedPayload",
    "DocumentRevisedPayload",
    # Documents
    "DocumentRevision",
    "compute_text_hash",
    # Story state
    "Character",
    "PlotEvent",
    "Fact",
    "ContinuityEvent",
    "Delivery",
    "ProjectPreference",
    "ConfirmedAssumptionPreference",
    "DeweightingPreference",
    "StoryClock",
    "Story",
    "StoryState",
    "StyleMemo",
    # Project
    "Project",
    # API
    "CreateProjectRequest",
    "AppendEventRequest",
    "ProjectResponse",
    "ProjectListResponse",
    "EventResponse",
    "EventListResponse",
    "StateResponse",
    "RebuildResponse",
    "ErrorResponse",
    "HealthResponse",
]
