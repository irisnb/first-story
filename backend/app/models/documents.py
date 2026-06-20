"""Document revision model for the screenplay manuscript.

Implements part of the document-revision spec:
- Each save is a revision recorded on the append-only event log.
- A revision carries the full prose content, a content hash, and the
  source span it covers, so extracted Facts can be located back to the text.

The event log remains the source of truth; the current document text in
StoryState is a projection rebuilt by replaying `document.revised` events.
"""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field

from .common import SourceSpan


def compute_text_hash(text: str) -> str:
    """Stable content hash for a manuscript revision (sha256 hex)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentRevision(BaseModel):
    """A single saved revision of the screenplay manuscript."""

    revision_id: str = Field(..., description="Stable identifier for this revision")
    document_id: str = Field(
        default="main", description="Document identifier (single manuscript for MVP)"
    )
    content: str = Field(..., description="Full manuscript prose at this revision")
    content_hash: str = Field(..., description="sha256 hex of the content")
    source_span: SourceSpan = Field(
        ..., description="Span this revision covers (whole document for a full save)"
    )
    revised_at: str = Field(..., description="ISO 8601 save time")
    source_event_id: str = Field(
        ..., description="SystemEvent.event_id that introduced this revision"
    )
    restored_from_revision_id: str | None = Field(
        None, description="Set when this revision is a restore of an older one"
    )
