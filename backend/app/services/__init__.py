"""Core services for the First Story backend."""

from .event_log import EventLogService
from .hub import Hub, HubEvent, HubResult, HubWriter, get_hub
from .alias_resolver import (
    AliasGroup,
    AliasResolutionResult,
    AliasResolverService,
)
from .document import DocumentService
from .contradiction import (
    ContradictionService,
    DetectedConflict,
    FactView,
)
from .dialogue import DialogueAgent, DialogueResult
from .evidence_card import CardActionResult, EvidenceCardService
from .export import to_fountain, to_plain_text
from .extraction import ExtractedFact, ExtractionResult, ExtractionService
from .extraction_pipeline import run_extraction_pipeline
from .fountain import ElementType, FountainElement, FountainParseResult, parse_fountain
from .llm_provider import (
    DeepSeekProvider,
    LLMNotConfiguredError,
    LLMProvider,
    LLMResponse,
    TokenUsage,
    TokenUsageTracker,
    build_provider,
    get_provider,
)
from .project import ProjectService
from .projector import ProjectorService

__all__ = [
    "EventLogService",
    "Hub",
    "HubEvent",
    "HubResult",
    "HubWriter",
    "get_hub",
    "AliasResolverService",
    "AliasGroup",
    "AliasResolutionResult",
    "ProjectorService",
    "ProjectService",
    "DocumentService",
    "ExtractionService",
    "ExtractedFact",
    "ExtractionResult",
    "run_extraction_pipeline",
    "ContradictionService",
    "DetectedConflict",
    "FactView",
    "DialogueAgent",
    "DialogueResult",
    "EvidenceCardService",
    "CardActionResult",
    "to_fountain",
    "to_plain_text",
    "parse_fountain",
    "FountainElement",
    "FountainParseResult",
    "ElementType",
    "LLMProvider",
    "DeepSeekProvider",
    "LLMResponse",
    "TokenUsage",
    "TokenUsageTracker",
    "LLMNotConfiguredError",
    "build_provider",
    "get_provider",
]
