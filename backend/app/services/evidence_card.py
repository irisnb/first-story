"""Evidence Card Service - user handling of continuity findings.

Implements the evidence-card-handling spec:

- A continuity finding is surfaced to the user as an *evidence card*. The user,
  not the system, decides what it means.

- ``ignore``: removes the card from active presentation. Judgment stays with the
  user; the system never forces a manuscript edit. When the user ignores a
  *category* of finding, a de-weighting rule is written to project preferences -
  the detection capability is NOT deleted; the same checks keep running in the
  background, future findings of that category are merely presented with lower
  priority. The rule (and history) can be adjusted or reversed later.

- ``accept``: marks the conflict as confirmed/resolved while preserving the
  event record for later reference.

Everything is append-only: ignoring or accepting records a new event and never
erases the original finding or facts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from .event_log import EventLogService

# Each ignore lowers the category priority by this much (negative = lower).
_DEWEIGHT_STEP = -0.2


@dataclass
class CardActionResult:
    """Outcome of an ignore/accept action on an evidence card."""

    continuity_event_id: str
    action: str
    deweighting_written: bool = False
    category: Optional[str] = None


class EvidenceCardService:
    """Records user decisions on continuity evidence cards."""

    def __init__(self, event_log: EventLogService):
        self.event_log = event_log
        from .hub import get_hub

        self._writer = get_hub().writer_for(event_log)

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _find_continuity_event(self, continuity_event_id: str) -> Optional[dict]:
        """Return the payload of the named continuity_event.created, if any."""
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype != "continuity_event.created":
                continue
            if event.payload.get("continuity_event_id") == continuity_event_id:
                return event.payload
        return None

    def ignore(
        self,
        continuity_event_id: str,
        *,
        user_explanation: Optional[str] = None,
        scope: str = "single_finding",
    ) -> Optional[CardActionResult]:
        """Ignore a card. With scope='category', also write a de-weighting rule.

        Returns None if the continuity event does not exist.
        """
        payload = self._find_continuity_event(continuity_event_id)
        if payload is None:
            return None

        self._writer.append(
            event_id=self._new_id("evt"),
            idempotency_key=f"ignore:{continuity_event_id}:{uuid.uuid4().hex[:8]}",
            event_type="continuity_event.ignored",
            payload={
                "continuity_event_id": continuity_event_id,
                "user_explanation": user_explanation,
                "scope": scope,
            },
            actor="user",
        )

        result = CardActionResult(
            continuity_event_id=continuity_event_id, action="ignored"
        )

        if scope == "category":
            category = payload.get("type", "")
            # De-weight the category - lower priority, NEVER disable detection.
            self._writer.append(
                event_id=self._new_id("evt"),
                idempotency_key=f"deweight:{category}:{continuity_event_id}",
                event_type="project_preference.deweighting_set",
                payload={
                    "category": category,
                    "weight_delta": _DEWEIGHT_STEP,
                    "reason": user_explanation
                    or f"用户忽略了「{category}」类提醒",
                    "scope": "project",
                },
                actor="user",
            )
            result.deweighting_written = True
            result.category = category

        return result

    def accept(
        self,
        continuity_event_id: str,
        *,
        resolution_fact_id: Optional[str] = None,
    ) -> Optional[CardActionResult]:
        """Accept a card - mark the conflict confirmed/resolved, keep the record.

        Returns None if the continuity event does not exist.
        """
        payload = self._find_continuity_event(continuity_event_id)
        if payload is None:
            return None

        self._writer.append(
            event_id=self._new_id("evt"),
            idempotency_key=f"resolve:{continuity_event_id}:{uuid.uuid4().hex[:8]}",
            event_type="continuity_event.resolved",
            payload={
                "continuity_event_id": continuity_event_id,
                "resolution_fact_id": resolution_fact_id,
            },
            actor="user",
        )
        return CardActionResult(
            continuity_event_id=continuity_event_id, action="accepted"
        )
