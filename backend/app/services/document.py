"""Document Service - save / list / restore manuscript revisions.

Implements the document-revision spec on top of the append-only event log:
- Saving appends a `document.revised` event (never overwrites).
- Listing replays the log to collect all revisions in order.
- Restoring an old revision appends a NEW `document.revised` event whose
  content is the old revision's content (restore = growth, not deletion).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from ..models import SystemEvent, compute_text_hash
from ..models.documents import DocumentRevision
from .event_log import EventLogService


class DocumentService:
    """Manages manuscript revisions through the event log."""

    def __init__(self, event_log: EventLogService):
        self.event_log = event_log
        from .hub import get_hub

        self._writer = get_hub().writer_for(event_log)

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def save_revision(
        self,
        content: str,
        *,
        document_id: str = "main",
        restored_from_revision_id: Optional[str] = None,
    ) -> DocumentRevision:
        """Append a new manuscript revision to the event log.

        Returns the persisted DocumentRevision.
        """
        revision_id = self._new_id("rev")
        event_id = self._new_id("evt")
        content_hash = compute_text_hash(content)
        source_span = {"start": 0, "end": len(content)}

        payload = {
            "revision_id": revision_id,
            "document_id": document_id,
            "content": content,
            "content_hash": content_hash,
            "source_span": source_span,
            "restored_from_revision_id": restored_from_revision_id,
        }

        seq, _was_new = self._writer.append(
            event_id=event_id,
            idempotency_key=revision_id,
            event_type="document.revised",
            payload=payload,
            actor="user",
        )

        # Read back the stored event to capture the authoritative timestamp.
        stored: SystemEvent = next(self.event_log.read_events(from_seq=seq, to_seq=seq))
        return self._revision_from_event(stored)

    def list_revisions(self, document_id: str = "main") -> list[DocumentRevision]:
        """Return all revisions for a document in save order (oldest first)."""
        revisions: list[DocumentRevision] = []
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype != "document.revised":
                continue
            if event.payload.get("document_id", "main") != document_id:
                continue
            revisions.append(self._revision_from_event(event))
        return revisions

    def get_revision(
        self, revision_id: str, document_id: str = "main"
    ) -> Optional[DocumentRevision]:
        """Find a specific revision by id."""
        for rev in self.list_revisions(document_id=document_id):
            if rev.revision_id == revision_id:
                return rev
        return None

    def restore_revision(
        self, revision_id: str, document_id: str = "main"
    ) -> Optional[DocumentRevision]:
        """Restore an old revision by appending it as a new revision.

        The old revision is never deleted; the restore is recorded as growth.
        Returns the new revision, or None if the target was not found.
        """
        target = self.get_revision(revision_id, document_id=document_id)
        if target is None:
            return None
        return self.save_revision(
            target.content,
            document_id=document_id,
            restored_from_revision_id=revision_id,
        )

    @staticmethod
    def _revision_from_event(event: SystemEvent) -> DocumentRevision:
        payload = event.payload
        revised_at = (
            event.timestamp.isoformat()
            if isinstance(event.timestamp, datetime)
            else str(event.timestamp)
        )
        return DocumentRevision(
            revision_id=payload.get("revision_id", ""),
            document_id=payload.get("document_id", "main"),
            content=payload.get("content", ""),
            content_hash=payload.get("content_hash", ""),
            source_span=payload.get("source_span", {"start": 0, "end": 0}),
            revised_at=revised_at,
            source_event_id=event.event_id,
            restored_from_revision_id=payload.get("restored_from_revision_id"),
        )
