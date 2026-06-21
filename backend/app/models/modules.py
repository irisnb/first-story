"""Module document models for the five story modules.

This aligns with the module-documents spec with provenance tracking.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# Module section definitions
MODULE_SECTIONS: dict[str, list[str]] = {
    "world": ["总述", "魔法/技术系统", "社会结构", "地理", "时间线锚点", "细节记录"],
    "characters": ["总述", "主要角色", "次要角色", "角色关系"],
    "plot": ["总述", "主线", "支线", "关键事件"],
    "theme": ["总述", "核心主题", "次要主题"],
    "structure": ["总述", "幕布结构", "节奏设计", "关键转折点"],
}

MODULE_NAMES = list(MODULE_SECTIONS.keys())


class ProvenanceEntry(BaseModel):
    """Provenance entry tracking the source of content."""

    type: str = Field(..., description="Source type: 'idea_card', 'chat_message', 'manual'")
    source_id: Optional[str] = Field(None, description="ID of the source (card_id, message_id, etc.)")
    revision_id: Optional[str] = Field(None, description="Revision ID if from idea card")
    excerpt: Optional[str] = Field(None, description="Original excerpt from source")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When this content was added"
    )


class ModuleSection(BaseModel):
    """A single section within a module document."""

    name: str = Field(..., description="Section name (e.g., '主要角色')")
    content: str = Field(default="", description="Section content as text")
    version: int = Field(default=1, description="Section version for optimistic locking")
    provenance: list[ProvenanceEntry] = Field(
        default_factory=list,
        description="List of provenance entries tracking content sources"
    )
    user_modified: bool = Field(
        default=False,
        description="Whether user has manually modified this section"
    )


class ModuleDocument(BaseModel):
    """A module document representing one of the five story modules.

    Each document is stored as a Markdown file and parsed into sections.
    """

    name: str = Field(..., description="Module name (world, characters, plot, theme, structure)")
    sections: dict[str, ModuleSection] = Field(
        default_factory=dict,
        description="Dictionary mapping section names to their content"
    )
    revision: int = Field(default=0, description="Document revision number")
    checksum: str = Field(default="", description="Content hash for optimistic locking")
    raw_content: str = Field(default="", description="Raw Markdown content")

    def get_section_content(self, section_name: str) -> str:
        """Get content of a specific section."""
        section = self.sections.get(section_name)
        return section.content if section else ""


class ModuleLock(BaseModel):
    """Lock state for a module document during editing."""

    module: str = Field(..., description="Module name being locked")
    user_id: str = Field(..., description="User ID holding the lock")
    locked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the lock was acquired"
    )
    ttl_seconds: int = Field(default=300, description="Lock TTL in seconds (default 5 min)")

    def is_expired(self) -> bool:
        """Check if the lock has expired."""
        elapsed = (datetime.now(timezone.utc) - self.locked_at).total_seconds()
        return elapsed > self.ttl_seconds

    def extend(self, additional_seconds: int = 300) -> None:
        """Extend the lock TTL."""
        self.locked_at = datetime.now(timezone.utc)
        self.ttl_seconds = additional_seconds


class ClassificationResult(BaseModel):
    """Result of classifying content into a module and section."""

    module: str = Field(..., description="Target module (world, characters, plot, theme, structure)")
    section: str = Field(..., description="Target section within the module")
    content: str = Field(..., description="Formatted content to append")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Classification confidence (0.0-1.0)"
    )


class ClassifyResponse(BaseModel):
    """Response from the classify endpoint."""

    classifications: list[ClassificationResult] = Field(
        default_factory=list,
        description="List of classification results"
    )
