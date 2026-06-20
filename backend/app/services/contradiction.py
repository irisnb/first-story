"""Contradiction Detection Service - deterministic hard-conflict checks.

Implements the contradiction-detection spec:

- Detects HARD continuity conflicts from extracted Facts, NOT from raw prose.
  The semantic judgment (is this character alive or dead here?) already lives
  in the LLM extraction stage as a normalized ``character_status`` enum.
  This service only does the *deterministic comparison* of those normalized
  statuses, so detection is reproducible and never re-guesses meaning from
  keywords (which was the original failure mode).

- A ContinuityEvent records ONLY evidence (the conflicting facts + their source
  spans). It MUST NOT contain a verdict, a fix suggestion, or a creative
  explanation. The user decides what it means.

- Runs as a post-save batch and is failure-isolated by its caller.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .event_log import EventLogService


@dataclass
class FactView:
    """A minimal read-model of a fact relevant to conflict detection."""

    fact_id: str
    content: str
    about_characters: list[str]
    # Per-character normalized status: {character_name: "alive"|"dead"|"unknown"}.
    character_statuses: dict[str, str]
    span: dict
    source_event_id: str


@dataclass
class DetectedConflict:
    """A detected hard conflict - evidence only, no verdict."""

    type: str
    character: str
    evidence_fact_ids: list[str]
    evidence: list[str] = field(default_factory=list)
    spans: list[dict] = field(default_factory=list)


class ContradictionService:
    """Detects hard continuity conflicts from committed Facts."""

    def __init__(self, event_log: EventLogService):
        self.event_log = event_log
        from .hub import get_hub

        self._writer = get_hub().writer_for(event_log)

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _load_alias_map(self) -> dict[str, str]:
        """Replay character.alias_bound events into {surface_name -> canonical}.

        This is a pure table lookup built from the alias-resolution pass. The
        detector uses it ONLY to normalize names before grouping; it never
        re-derives identity or meaning from keywords here.
        """
        mapping: dict[str, str] = {}
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype != "character.alias_bound":
                continue
            p = event.payload
            canonical = p.get("canonical_name")
            if not canonical:
                continue
            for alias in p.get("aliases", []):
                if alias:
                    mapping[alias] = canonical
            mapping.setdefault(canonical, canonical)
        return mapping

    def _load_facts(self) -> list[FactView]:
        alias_map = self._load_alias_map()
        facts: list[FactView] = []
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype != "fact.created":
                continue
            p = event.payload
            # Only committed facts enter contradiction detection. Candidate facts
            # are chat brainstorms / hypotheses - a tentative idea must NEVER be
            # flagged as a continuity conflict. Historical facts (no field)
            # default to committed.
            if p.get("acceptance_status", "committed") == "candidate":
                continue
            about_raw = p.get("about_character_names", [])
            statuses_raw = self._normalize_statuses(p, about_raw)
            # Canonicalize surface names to their resolved identity so that the
            # same person referred to by different names is grouped together.
            about = [alias_map.get(n, n) for n in about_raw]
            statuses = self._canonicalize_statuses(statuses_raw, alias_map)
            facts.append(
                FactView(
                    fact_id=p.get("fact_id", ""),
                    content=p.get("content", ""),
                    about_characters=about,
                    character_statuses=statuses,
                    span=p.get("source_span", {"start": 0, "end": 0}),
                    source_event_id=event.event_id,
                )
            )
        return facts

    @staticmethod
    def _canonicalize_statuses(
        statuses: dict[str, str], alias_map: dict[str, str]
    ) -> dict[str, str]:
        """Remap status keys to canonical names.

        If two surface names for the same person carry conflicting statuses
        WITHIN one fact (rare), the stronger 'dead' signal is preserved over
        'alive', and an explicit status over 'unknown' - so collapsing names
        never silently drops a death assertion.
        """
        rank = {"unknown": 0, "alive": 1, "dead": 2}
        merged: dict[str, str] = {}
        for name, status in statuses.items():
            canonical = alias_map.get(name, name)
            current = merged.get(canonical)
            if current is None or rank.get(status, 0) > rank.get(current, 0):
                merged[canonical] = status
        return merged

    @staticmethod
    def _normalize_statuses(payload: dict, about: list[str]) -> dict[str, str]:
        """Read per-character statuses, broadcasting legacy single values.

        New events carry ``character_statuses`` (a per-character map). Older
        events carry a single ``character_status`` that applied to every named
        character; for replay compatibility that value is broadcast across the
        fact's characters. No semantics are re-derived here - this only adapts
        the persisted shape.
        """
        raw_map = payload.get("character_statuses")
        if isinstance(raw_map, dict):
            return {
                name: (value or "unknown").lower()
                for name, value in raw_map.items()
                if name
            }
        legacy = (payload.get("character_status") or "unknown").lower()
        return {name: legacy for name in about}

    def detect(self) -> list[DetectedConflict]:
        """Return hard conflicts among all committed facts (no side effects)."""
        facts = self._load_facts()
        return self._detect_status_conflicts(facts)

    @staticmethod
    def _detect_status_conflicts(facts: list[FactView]) -> list[DetectedConflict]:
        """Find characters asserted both alive and dead.

        This is a deterministic comparison of normalized status enums - the
        meaning was already decided by the extraction LLM, not re-derived here.
        """
        # character -> {status: [FactView, ...]}
        by_char: dict[str, dict[str, list[FactView]]] = {}
        for fact in facts:
            for name, status in fact.character_statuses.items():
                if status not in ("alive", "dead"):
                    continue
                by_char.setdefault(name, {}).setdefault(status, []).append(fact)

        conflicts: list[DetectedConflict] = []
        for name, statuses in by_char.items():
            if "alive" in statuses and "dead" in statuses:
                evidence_facts = statuses["dead"] + statuses["alive"]
                conflicts.append(
                    DetectedConflict(
                        type="character_status_conflict",
                        character=name,
                        evidence_fact_ids=[f.fact_id for f in evidence_facts],
                        evidence=[f.content for f in evidence_facts],
                        spans=[f.span for f in evidence_facts],
                    )
                )
        return conflicts

    def _existing_signatures(self) -> set[frozenset]:
        """Signatures of continuity events already recorded (for idempotency)."""
        sigs: set[frozenset] = set()
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype != "continuity_event.created":
                continue
            p = event.payload
            ids = p.get("evidence_fact_ids", [])
            names = p.get("involved_character_names", [])
            sigs.add(frozenset(ids) | frozenset(f"char::{n}" for n in names))
        return sigs

    def run_batch(self, *, document_id: str = "main", revision: str = "") -> list[str]:
        """Detect conflicts and record new ContinuityEvents on the log.

        Returns the list of newly created continuity_event ids. Does not record
        a finding whose exact evidence set was already recorded.
        """
        conflicts = self.detect()
        existing = self._existing_signatures()
        created: list[str] = []

        for conflict in conflicts:
            signature = frozenset(conflict.evidence_fact_ids) | frozenset(
                [f"char::{conflict.character}"]
            )
            if signature in existing:
                continue
            ce_id = self._new_id("ce")
            event_id = self._new_id("evt")
            self._writer.append(
                event_id=event_id,
                idempotency_key=f"continuity:{ce_id}",
                event_type="continuity_event.created",
                payload={
                    "continuity_event_id": ce_id,
                    "type": conflict.type,
                    "severity": "P2",
                    "contradiction_confidence": 0.8,
                    # Evidence ONLY - no verdict, no suggestion, no explanation.
                    "evidence_fact_ids": conflict.evidence_fact_ids,
                    "evidence": conflict.evidence,
                    "evidence_spans": conflict.spans,
                    "affected_modules": ["character"],
                    "status": "queued",
                    "title": None,
                    "involved_character_names": [conflict.character],
                },
                actor="continuity_agent",
            )
            existing.add(signature)
            created.append(ce_id)

        return created
