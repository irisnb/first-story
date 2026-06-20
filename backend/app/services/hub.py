"""Thin Runtime Hub - in-process service router + per-project write gate.

Implements the agent-hub spec (design D1):

- The Hub is the single coordination point for ALL event-log writes. It owns a
  per-project re-entrant lock and a per-project cached ``EventLogService`` so
  that the full read-modify-write of a write (scan file -> compute seq ->
  append) is serialized and ``seq`` stays monotonic. Without a single cached
  instance, two concurrently-built ``EventLogService`` objects would each scan
  the file, both compute the same ``_next_seq``, and write a duplicate seq.

- Business code never calls ``EventLogService.append_event`` directly. Instead
  it writes through a :class:`HubWriter` obtained from the Hub
  (``writer.append(...)``), which acquires the project lock around the append.
  This is enforced by an architecture test (see ``tests/test_hub.py``): the only
  files allowed to call ``append_event(`` are ``event_log.py`` and ``hub.py``.

- ``dispatch`` routes a structured :class:`HubEvent` to a registered specialist
  handler and returns a structured :class:`HubResult`. The Hub speaks ONLY
  structured fields - it never produces user-facing natural language and never
  judges creative content (AGENTS.md anti-drift rule 1). Handlers are
  registered by other layers so the Hub never imports specialist services
  itself (avoids the god-object drift).

V1 is single-process: the Hub is an app-level singleton holding in-memory locks.
Multi-worker deployment would need an external lock and is out of scope.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Optional

from .event_log import EventLogService

logger = logging.getLogger("first_story.hub")


@dataclass
class HubEvent:
    """A structured request sent to the Hub for routing.

    Carries ONLY machine-readable fields - never user-facing prose.
    """

    type: str
    project_id: str
    payload: dict = field(default_factory=dict)


@dataclass
class HubResult:
    """A structured result returned from :meth:`Hub.dispatch`.

    Carries ONLY machine-readable fields. There is intentionally NO field for
    user-facing natural language: the Hub must not write reminders, explain
    findings, or judge creative work. The dialogue gateway owns all user prose.
    """

    type: str
    ok: bool
    data: dict = field(default_factory=dict)
    error: Optional[str] = None


# A dispatch handler takes the structured event and returns structured data.
HubHandler = Callable[[HubEvent], dict]


class HubWriter:
    """A project-bound write handle that serializes appends under the Hub lock.

    Obtained via :meth:`Hub.writer_for`. Business services hold one of these
    instead of calling ``EventLogService.append_event`` directly, so every
    write goes through the same per-project lock.
    """

    def __init__(self, event_log: EventLogService, lock: threading.RLock):
        self._event_log = event_log
        self._lock = lock

    def append(
        self,
        *,
        event_id: str,
        idempotency_key: str,
        event_type: str,
        payload: dict,
        base_state_version: int = 0,
        actor: str = "user",
        batch_id: Optional[str] = None,
        schema_version: str = "1.0",
    ) -> tuple[int, bool]:
        """Append an event under the project write lock.

        Mirrors :meth:`EventLogService.append_event` and returns the same
        ``(seq, was_new)`` tuple. The lock guarantees the scan-compute-append
        read-modify-write is atomic with respect to other writers on the same
        project, so ``seq`` never collides.
        """
        with self._lock:
            return self._event_log.append_event(
                event_id=event_id,
                idempotency_key=idempotency_key,
                event_type=event_type,
                payload=payload,
                base_state_version=base_state_version,
                actor=actor,
                batch_id=batch_id,
                schema_version=schema_version,
            )


class Hub:
    """In-process runtime Hub: write gate + service router.

    The Hub is deliberately thin. It does not import specialist services, does
    not generate user prose, and does not judge creative content. It only:
    routes structured events, serializes writes, and caches one event-log
    instance per project.
    """

    def __init__(self) -> None:
        self._locks: dict[str, threading.RLock] = {}
        self._event_logs: dict[str, EventLogService] = {}
        self._handlers: dict[str, HubHandler] = {}
        # Guards the registry maps themselves (creating locks / caching logs).
        self._registry_lock = threading.Lock()

    # ----------------------------------------------------------- write gate

    @staticmethod
    def _key(events_dir: Path) -> str:
        """Stable per-project key from the events directory path."""
        return str(Path(events_dir).resolve())

    def _lock_for(self, events_dir: Path) -> threading.RLock:
        key = self._key(events_dir)
        with self._registry_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.RLock()
                self._locks[key] = lock
            return lock

    def get_event_log(self, events_dir: Path) -> EventLogService:
        """Return the single cached ``EventLogService`` for a project.

        Caching one instance per project is what makes the per-project lock
        actually prevent duplicate ``seq`` - all writers share the same
        in-memory ``_next_seq``.
        """
        key = self._key(events_dir)
        with self._registry_lock:
            event_log = self._event_logs.get(key)
            if event_log is None:
                event_log = EventLogService(Path(events_dir))
                self._event_logs[key] = event_log
            return event_log

    def writer_for(self, event_log: EventLogService) -> HubWriter:
        """Return a write handle bound to this project's lock.

        Accepts an existing ``EventLogService`` so service constructors stay
        unchanged; the lock is keyed by the log's events directory.
        """
        lock = self._lock_for(event_log.events_dir)
        return HubWriter(event_log, lock)

    @contextmanager
    def project_lock(self, event_log: EventLogService) -> Iterator[None]:
        """Hold the per-project write lock across a multi-step read-modify-write.

        Used by operations like manuscript adoption that must read current
        state, modify it, and append - all atomically. Re-entrant: code inside
        may also call ``writer.append`` (same RLock) without deadlocking.
        """
        lock = self._lock_for(event_log.events_dir)
        with lock:
            yield

    # -------------------------------------------------------------- routing

    def register(self, event_type: str, handler: HubHandler) -> None:
        """Register a specialist handler for a structured event type.

        Registration (rather than the Hub importing specialists) keeps the Hub
        thin and prevents it from depending on extraction/contradiction/etc.
        """
        with self._registry_lock:
            self._handlers[event_type] = handler

    def dispatch(self, event: HubEvent) -> HubResult:
        """Route a structured event to its handler, isolating failures.

        Never raises back to the caller: a specialist failure is swallowed and
        recorded as ``ok=False`` so background work never blocks the user
        (AGENTS.md failure-isolation rule). Returns ONLY structured data.
        """
        handler = self._handlers.get(event.type)
        if handler is None:
            return HubResult(
                type=event.type, ok=False, error=f"no handler for '{event.type}'"
            )
        try:
            data = handler(event)
            return HubResult(type=event.type, ok=True, data=data or {})
        except Exception as exc:  # noqa: BLE001 - isolate; never block the user
            logger.warning("hub dispatch '%s' failed: %s", event.type, exc)
            return HubResult(type=event.type, ok=False, error=str(exc))


# App-level singleton. V1 is single-process so an in-memory Hub is sufficient.
_hub: Optional[Hub] = None
_hub_lock = threading.Lock()


def get_hub() -> Hub:
    """Return the process-wide Hub singleton."""
    global _hub
    if _hub is None:
        with _hub_lock:
            if _hub is None:
                _hub = Hub()
    return _hub
